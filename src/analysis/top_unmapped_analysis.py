"""
Top Unmapped Hours Analysis Module for Workforce Analytics.

This module identifies employees with the highest unmapped hours across all categories
and provides ranking and analysis for reporting. Similar to overtime analysis but
focuses on unmapped work categories.

The system:
- Filters data to include only unmapped role categories
- Aggregates unmapped hours across all categories per employee
- Determines primary unmapped category by most hours worked
- Provides ranking and statistical analysis of unmapped patterns
- Supports configurable top-N reporting

Example Usage:
    from src.analysis.top_unmapped_analysis import calculate_top_unmapped_analysis
    
    # Calculate top 3 unmapped employees for a facility
    unmapped_result = calculate_top_unmapped_analysis(
        facility_df=filtered_facility_data,
        facility_name="Ansley Park",
        analysis_start_date=start_date,
        analysis_end_date=end_date,
        top_count=3
    )
"""

import logging
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional
from collections import defaultdict

from src.models.data_models import UnmappedEmployee, TopUnmappedAnalysis, UnmappedFunctionGroup
from src.utils.role_display_mapper import get_short_display_name, get_role_function
from config.constants import FileColumns

logger = logging.getLogger(__name__)


def is_unmapped_role(role: str) -> bool:
    """
    Check if a role is an unmapped category.
    
    Args:
        role: Role name to check
        
    Returns:
        True if the role is unmapped, False otherwise
    """
    if pd.isna(role) or role in ["NULL", ""]:
        return False
    
    unmapped_categories = [
        "Unmapped Nursing",
        "Unmapped Dietary", 
        "Unmapped Hskp",
        "Unmapped Life Enrichment",
        "Unmapped Maintenance",
        "Unmapped Admin",
        "Other Unmapped"
    ]
    
    return role in unmapped_categories


def get_employee_primary_unmapped_category(employee_df: pd.DataFrame) -> str:
    """
    Determine the primary unmapped category for an employee based on most hours worked.
    
    Args:
        employee_df: DataFrame containing all unmapped records for a single employee
        
    Returns:
        Primary unmapped category name (most common category by total hours)
    """
    if employee_df.empty:
        return "Other Unmapped"
    
    # Filter to only unmapped roles
    unmapped_df = employee_df[
        employee_df[FileColumns.FACILITY_STAFF_ROLE_NAME].apply(is_unmapped_role)
    ]
    
    if unmapped_df.empty:
        return "Other Unmapped"
    
    # Group by category and sum hours to find the category with most hours
    category_hours = unmapped_df.groupby(FileColumns.FACILITY_STAFF_ROLE_NAME)[FileColumns.FACILITY_TOTAL_HOURS].sum()
    
    if category_hours.empty:
        return "Other Unmapped"
    
    # Return the category with the highest total hours
    primary_category = category_hours.idxmax()
    return primary_category if pd.notna(primary_category) else "Other Unmapped"


def calculate_employee_unmapped_hours(employee_df: pd.DataFrame, 
                                    employee_id: str, 
                                    employee_name: str,
                                    role: str) -> Optional[Dict]:
    """
    Calculate unmapped hours statistics for a single employee-role combination.
    
    Args:
        employee_df: DataFrame containing all records for the employee-role combination
        employee_id: Employee identifier
        employee_name: Employee name
        role: Role being worked by the employee
        
    Returns:
        Dictionary with unmapped hours statistics or None if no unmapped hours
    """
    if employee_df.empty:
        return None
    
    # Filter to only unmapped work
    unmapped_df = employee_df[
        employee_df[FileColumns.FACILITY_STAFF_ROLE_NAME].apply(is_unmapped_role)
    ]
    
    if unmapped_df.empty:
        return None
    
    # Determine primary unmapped category (for display purposes)
    primary_category = get_employee_primary_unmapped_category(employee_df)
    logger.debug(f"Employee {employee_name} primary unmapped category: {primary_category}")
    
    # Calculate total unmapped hours across all categories
    total_unmapped_hours = 0.0
    days_with_unmapped = 0
    
    for _, row in unmapped_df.iterrows():
        unmapped_hours = row[FileColumns.FACILITY_TOTAL_HOURS]
        
        if unmapped_hours > 0:
            total_unmapped_hours += unmapped_hours
            days_with_unmapped += 1
    
    # Only return data if employee has unmapped hours
    if total_unmapped_hours <= 0:
        return None
    
    # Calculate average daily unmapped hours (only for days with unmapped work)
    average_daily_unmapped = total_unmapped_hours / max(days_with_unmapped, 1)
    
    return {
        'employee_id': employee_id,
        'employee_name': employee_name,
        'role': role,
        'total_unmapped_hours': total_unmapped_hours,
        'days_with_unmapped': days_with_unmapped,
        'average_daily_unmapped': average_daily_unmapped,
        'primary_category': primary_category
    }


def calculate_top_unmapped_analysis(facility_df: pd.DataFrame,
                                  facility_name: str,
                                  analysis_start_date: datetime,
                                  analysis_end_date: datetime,
                                  top_count: int = 3) -> TopUnmappedAnalysis:
    """
    Calculate top unmapped hours analysis for a facility.
    
    Args:
        facility_df: DataFrame with facility hours data (already filtered by date)
        facility_name: Name of the facility
        analysis_start_date: Start date of analysis period
        analysis_end_date: End date of analysis period
        top_count: Number of top unmapped employees to include
        
    Returns:
        TopUnmappedAnalysis object with top employees and summary statistics
    """
    logger.info(f"Calculating top unmapped analysis for {facility_name} from {analysis_start_date} to {analysis_end_date}")
    
    # Debug: Log details about the facility data received
    logger.debug(f"Facility DataFrame shape: {facility_df.shape}")
    if not facility_df.empty:
        unmapped_records = facility_df[facility_df[FileColumns.FACILITY_STAFF_ROLE_NAME].apply(is_unmapped_role)]
        logger.debug(f"Records with unmapped roles: {len(unmapped_records)}")
    
    if facility_df.empty:
        logger.warning(f"No facility data provided for unmapped analysis: {facility_name}")
        return TopUnmappedAnalysis(
            facility=facility_name,
            top_employees=[],
            total_employees_with_unmapped=0,
            top_count_requested=top_count,
            total_unmapped_hours_facility=0.0,
            analysis_period_start=analysis_start_date,
            analysis_period_end=analysis_end_date
        )
    
    # Group by employee to calculate individual unmapped hours
    employee_unmapped_data = []
    total_facility_unmapped = 0.0
    
    # Group by employee ID, name, AND role to treat each employee-role combination independently
    employee_role_groups = facility_df.groupby([FileColumns.FACILITY_EMPLOYEE_ID, FileColumns.FACILITY_EMPLOYEE_NAME, FileColumns.FACILITY_STAFF_ROLE_NAME])
    
    logger.debug(f"Processing {len(employee_role_groups)} employee-role combinations for unmapped analysis")
    
    for (employee_id, employee_name, role), employee_df in employee_role_groups:
        # Skip if employee info is missing
        if pd.isna(employee_id) or pd.isna(employee_name) or pd.isna(role):
            logger.debug(f"Skipping employee with missing ID, name, or role: {employee_id}, {employee_name}, {role}")
            continue
        
        try:
            # Calculate unmapped hours for this employee-role combination
            unmapped_stats = calculate_employee_unmapped_hours(employee_df, str(employee_id), str(employee_name), str(role))
            
            if unmapped_stats:
                logger.debug(f"Employee {employee_name} has {unmapped_stats['total_unmapped_hours']:.2f} unmapped hours")
                employee_unmapped_data.append(unmapped_stats)
                total_facility_unmapped += unmapped_stats['total_unmapped_hours']
            else:
                logger.debug(f"Employee {employee_name} has no unmapped hours")
        except Exception as e:
            logger.warning(f"Error calculating unmapped hours for employee {employee_name} ({employee_id}): {str(e)}")
            continue
    
    # Sort employees by total unmapped hours (descending)
    employee_unmapped_data.sort(key=lambda x: x['total_unmapped_hours'], reverse=True)
    
    # Group employees by function (clinical vs non-clinical) based on their primary unmapped category
    clinical_employees = []
    non_clinical_employees = []
    
    for emp_data in employee_unmapped_data:
        # Determine function of the employee's primary unmapped category
        try:
            category_function = get_role_function(emp_data['primary_category'])
            logger.debug(f"Employee {emp_data['employee_name']} primary category '{emp_data['primary_category']}' classified as: {category_function}")
        except KeyError:
            logger.warning(f"No function found for category '{emp_data['primary_category']}', defaulting to non-clinical")
            category_function = "non-clinical"
        except Exception as e:
            logger.error(f"Error getting function for category '{emp_data['primary_category']}': {str(e)}, defaulting to non-clinical")
            category_function = "non-clinical"
        
        # Convert category to short display name for reporting
        try:
            display_category = get_short_display_name(emp_data['primary_category'])
        except KeyError:
            logger.warning(f"No short display name found for category '{emp_data['primary_category']}', using original")
            display_category = emp_data['primary_category']
        
        # Create UnmappedEmployee object
        unmapped_employee = UnmappedEmployee(
            employee_id=emp_data['employee_id'],
            employee_name=emp_data['employee_name'],
            role=emp_data['role'],
            total_unmapped_hours=emp_data['total_unmapped_hours'],
            days_with_unmapped=emp_data['days_with_unmapped'],
            average_daily_unmapped=emp_data['average_daily_unmapped'],
            primary_category=display_category,
            rank=1  # Will be set properly when creating function groups
        )
        
        # Group by function
        if category_function == "clinical":
            clinical_employees.append(unmapped_employee)
        else:
            non_clinical_employees.append(unmapped_employee)
    
    # Create function groups with top N employees each
    clinical_group = None
    non_clinical_group = None
    
    if clinical_employees:
        # Set ranks for clinical employees
        for rank, emp in enumerate(clinical_employees[:top_count], 1):
            emp.rank = rank
        
        clinical_total_hours = sum(emp.total_unmapped_hours for emp in clinical_employees)
        clinical_group = UnmappedFunctionGroup(
            function="clinical",
            display_name="Clinical Associates",
            employees=clinical_employees[:top_count],
            total_unmapped_hours=clinical_total_hours,
            total_employees_in_function=len(clinical_employees)
        )
    
    if non_clinical_employees:
        # Set ranks for non-clinical employees
        for rank, emp in enumerate(non_clinical_employees[:top_count], 1):
            emp.rank = rank
        
        non_clinical_total_hours = sum(emp.total_unmapped_hours for emp in non_clinical_employees)
        non_clinical_group = UnmappedFunctionGroup(
            function="non-clinical",
            display_name="Non-Clinical Associates",
            employees=non_clinical_employees[:top_count],
            total_unmapped_hours=non_clinical_total_hours,
            total_employees_in_function=len(non_clinical_employees)
        )
    
    # Create legacy top N list (for backward compatibility)
    top_employees = []
    for rank, emp_data in enumerate(employee_unmapped_data[:top_count], 1):
        try:
            display_category = get_short_display_name(emp_data['primary_category'])
        except KeyError:
            display_category = emp_data['primary_category']
        
        unmapped_employee = UnmappedEmployee(
            employee_id=emp_data['employee_id'],
            employee_name=emp_data['employee_name'],
            role=emp_data['role'],
            total_unmapped_hours=emp_data['total_unmapped_hours'],
            days_with_unmapped=emp_data['days_with_unmapped'],
            average_daily_unmapped=emp_data['average_daily_unmapped'],
            primary_category=display_category,
            rank=rank
        )
        top_employees.append(unmapped_employee)
    
    logger.info(f"Unmapped analysis complete: {len(employee_unmapped_data)} employees with unmapped hours, "
                f"{total_facility_unmapped:.2f} total facility unmapped hours")
    logger.info(f"Clinical employees with unmapped hours: {len(clinical_employees)}, "
                f"Non-clinical employees with unmapped hours: {len(non_clinical_employees)}")
    logger.info(f"Clinical group created: {clinical_group is not None}, Non-clinical group created: {non_clinical_group is not None}")
    
    return TopUnmappedAnalysis(
        facility=facility_name,
        top_employees=top_employees,
        clinical_group=clinical_group,
        non_clinical_group=non_clinical_group,
        total_employees_with_unmapped=len(employee_unmapped_data),
        top_count_requested=top_count,
        total_unmapped_hours_facility=total_facility_unmapped,
        analysis_period_start=analysis_start_date,
        analysis_period_end=analysis_end_date
    )


def get_unmapped_summary_statistics(unmapped_analysis: TopUnmappedAnalysis) -> Dict[str, float]:
    """
    Calculate summary statistics from unmapped analysis results.
    
    Args:
        unmapped_analysis: TopUnmappedAnalysis object
        
    Returns:
        Dictionary with summary statistics
    """
    if not unmapped_analysis.top_employees:
        return {
            'average_unmapped_per_employee': 0.0,
            'highest_individual_unmapped': 0.0,
            'average_days_with_unmapped': 0.0,
            'unmapped_concentration_ratio': 0.0  # Top N vs total facility unmapped
        }
    
    # Calculate statistics from top employees (representative sample)
    total_top_unmapped = sum(emp.total_unmapped_hours for emp in unmapped_analysis.top_employees)
    total_top_days = sum(emp.days_with_unmapped for emp in unmapped_analysis.top_employees)
    
    highest_unmapped = max(emp.total_unmapped_hours for emp in unmapped_analysis.top_employees)
    average_unmapped = total_top_unmapped / len(unmapped_analysis.top_employees)
    average_days = total_top_days / len(unmapped_analysis.top_employees)
    
    # Calculate concentration ratio (what % of total facility unmapped is from top N employees)
    concentration_ratio = 0.0
    if unmapped_analysis.total_unmapped_hours_facility > 0:
        concentration_ratio = (total_top_unmapped / unmapped_analysis.total_unmapped_hours_facility) * 100
    
    return {
        'average_unmapped_per_employee': average_unmapped,
        'highest_individual_unmapped': highest_unmapped,
        'average_days_with_unmapped': average_days,
        'unmapped_concentration_ratio': concentration_ratio
    }


# Initialize logging for this module
logger.info("Top unmapped hours analysis module initialized")