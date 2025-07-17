"""
Overtime Analysis Module for Workforce Analytics.

This module calculates overtime hours for employees based on role-specific standard shift hours.
It identifies employees who worked more than their expected shift hours and provides
ranking and analysis for reporting.

The system:
- Uses role-specific standard shift hours from the role display mapper
- Calculates daily overtime by comparing actual hours to standard shift hours
- Aggregates overtime across the analysis period
- Provides ranking and statistical analysis of overtime patterns
- Supports configurable top-N reporting

Example Usage:
    from src.analysis.overtime_analysis import calculate_overtime_analysis
    
    # Calculate top 5 overtime employees for a facility
    overtime_result = calculate_overtime_analysis(
        facility_df=filtered_facility_data,
        facility_name="Ansley Park",
        analysis_start_date=start_date,
        analysis_end_date=end_date,
        top_count=5
    )
"""

import logging
import pandas as pd
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from collections import defaultdict

from src.models.data_models import OvertimeEmployee, OvertimeAnalysis
from src.utils.role_display_mapper import get_standard_shift_hours, get_short_display_name
from config.constants import FileColumns

logger = logging.getLogger(__name__)


def calculate_daily_overtime(actual_hours: float, standard_shift_hours: float) -> float:
    """
    Calculate overtime hours for a single day.
    
    Args:
        actual_hours: Hours actually worked
        standard_shift_hours: Expected hours for the role
        
    Returns:
        Overtime hours (0.0 if no overtime)
    """
    if actual_hours <= standard_shift_hours:
        return 0.0
    return actual_hours - standard_shift_hours


def get_employee_primary_role(employee_df: pd.DataFrame) -> str:
    """
    Determine the primary role for an employee based on most hours worked.
    
    Args:
        employee_df: DataFrame containing all records for a single employee
        
    Returns:
        Primary role name (most common role by total hours)
    """
    if employee_df.empty:
        return "Unknown"
    
    # Filter out NULL/NaN roles and unmapped categories
    valid_roles_df = employee_df[
        employee_df[FileColumns.FACILITY_STAFF_ROLE_NAME].notna() & 
        (employee_df[FileColumns.FACILITY_STAFF_ROLE_NAME] != "NULL") &
        (employee_df[FileColumns.FACILITY_STAFF_ROLE_NAME] != "") &
        (~employee_df[FileColumns.FACILITY_STAFF_ROLE_NAME].str.startswith("Unmapped", na=False)) &
        (employee_df[FileColumns.FACILITY_STAFF_ROLE_NAME] != "Other Unmapped")
    ]
    
    if valid_roles_df.empty:
        return "Unknown"
    
    # Group by role and sum hours to find the role with most hours
    role_hours = valid_roles_df.groupby(FileColumns.FACILITY_STAFF_ROLE_NAME)[FileColumns.FACILITY_TOTAL_HOURS].sum()
    
    if role_hours.empty:
        return "Unknown"
    
    # Return the role with the highest total hours
    primary_role = role_hours.idxmax()
    return primary_role if pd.notna(primary_role) else "Unknown"


def calculate_employee_overtime(employee_df: pd.DataFrame, 
                              employee_id: str, 
                              employee_name: str) -> Optional[Dict]:
    """
    Calculate overtime statistics for a single employee.
    
    Args:
        employee_df: DataFrame containing all records for the employee
        employee_id: Employee identifier
        employee_name: Employee name
        
    Returns:
        Dictionary with overtime statistics or None if no overtime
    """
    if employee_df.empty:
        return None
    
    # Filter out NULL/NaN roles and unmapped categories for overtime calculation
    valid_work_df = employee_df[
        employee_df[FileColumns.FACILITY_STAFF_ROLE_NAME].notna() & 
        (employee_df[FileColumns.FACILITY_STAFF_ROLE_NAME] != "NULL") &
        (employee_df[FileColumns.FACILITY_STAFF_ROLE_NAME] != "") &
        (~employee_df[FileColumns.FACILITY_STAFF_ROLE_NAME].str.startswith("Unmapped", na=False)) &
        (employee_df[FileColumns.FACILITY_STAFF_ROLE_NAME] != "Other Unmapped")
    ]
    
    if valid_work_df.empty:
        return None
    
    # Determine primary role (for display purposes)
    primary_role = get_employee_primary_role(employee_df)
    logger.debug(f"Employee {employee_name} primary role: {primary_role}")
    
    # Calculate role-specific overtime for each work record
    total_overtime_hours = 0.0
    days_with_overtime = 0
    
    for _, row in valid_work_df.iterrows():
        role = row[FileColumns.FACILITY_STAFF_ROLE_NAME]
        actual_hours = row[FileColumns.FACILITY_TOTAL_HOURS]
        
        # Get standard shift hours for THIS specific role
        try:
            role_standard_hours = get_standard_shift_hours(role)
            logger.debug(f"Employee {employee_name} worked {actual_hours} hours as {role} (standard: {role_standard_hours})")
        except KeyError:
            logger.warning(f"No standard shift hours found for role '{role}', skipping record")
            continue
        
        # Skip unmapped roles (they have 0.0 standard hours)
        if role_standard_hours == 0.0:
            logger.debug(f"Skipping unmapped/unknown role '{role}' for overtime calculation")
            continue
        
        # Calculate overtime for this specific role/day
        daily_overtime = calculate_daily_overtime(actual_hours, role_standard_hours)
        
        if daily_overtime > 0:
            total_overtime_hours += daily_overtime
            days_with_overtime += 1
            logger.debug(f"Employee {employee_name} had {daily_overtime:.2f} overtime hours as {role}")
    
    # Only return data if employee has overtime
    if total_overtime_hours <= 0:
        return None
    
    # Calculate average daily overtime (only for days with overtime)
    average_daily_overtime = total_overtime_hours / max(days_with_overtime, 1)
    
    return {
        'employee_id': employee_id,
        'employee_name': employee_name,
        'total_overtime_hours': total_overtime_hours,
        'days_with_overtime': days_with_overtime,
        'average_daily_overtime': average_daily_overtime,
        'primary_role': primary_role
    }


def calculate_overtime_analysis(facility_df: pd.DataFrame,
                              facility_name: str,
                              analysis_start_date: datetime,
                              analysis_end_date: datetime,
                              top_count: int = 3) -> OvertimeAnalysis:
    """
    Calculate overtime analysis for a facility.
    
    Args:
        facility_df: DataFrame with facility hours data (already filtered by date)
        facility_name: Name of the facility
        analysis_start_date: Start date of analysis period
        analysis_end_date: End date of analysis period
        top_count: Number of top overtime employees to include
        
    Returns:
        OvertimeAnalysis object with top employees and summary statistics
    """
    logger.info(f"Calculating overtime analysis for {facility_name} from {analysis_start_date} to {analysis_end_date}")
    
    # Debug: Log details about the facility data received
    logger.debug(f"Facility DataFrame shape: {facility_df.shape}")
    if not facility_df.empty:
        logger.debug(f"Facility DataFrame columns: {list(facility_df.columns)}")
        logger.debug(f"Unique facilities in data: {facility_df[FileColumns.FACILITY_LOCATION_NAME].unique() if FileColumns.FACILITY_LOCATION_NAME in facility_df.columns else 'NO FACILITY COLUMN'}")
        high_hours = facility_df[facility_df[FileColumns.FACILITY_TOTAL_HOURS] > 8.0] if FileColumns.FACILITY_TOTAL_HOURS in facility_df.columns else pd.DataFrame()
        logger.debug(f"Records with > 8 hours: {len(high_hours)}")
    
    if facility_df.empty:
        logger.warning(f"No facility data provided for overtime analysis: {facility_name}")
        return OvertimeAnalysis(
            facility=facility_name,
            top_employees=[],
            total_employees_with_overtime=0,
            top_count_requested=top_count,
            total_overtime_hours_facility=0.0,
            analysis_period_start=analysis_start_date,
            analysis_period_end=analysis_end_date
        )
    
    # Group by employee to calculate individual overtime
    employee_overtime_data = []
    total_facility_overtime = 0.0
    
    # Clean the data first - remove any header contamination
    clean_df = facility_df.copy()
    
    # Filter out any rows where employee_id might be the header text
    if FileColumns.FACILITY_EMPLOYEE_ID in clean_df.columns:
        # Remove rows where employee ID contains header text
        header_mask = clean_df[FileColumns.FACILITY_EMPLOYEE_ID].astype(str).str.contains('EMPLOYEE', na=False, case=False)
        if header_mask.any():
            logger.warning(f"Found {header_mask.sum()} header rows in data, removing them")
            clean_df = clean_df[~header_mask]
    
    # Group by employee ID and name
    employee_groups = clean_df.groupby([FileColumns.FACILITY_EMPLOYEE_ID, FileColumns.FACILITY_EMPLOYEE_NAME])
    
    logger.debug(f"Processing {len(employee_groups)} employee groups")
    
    for (employee_id, employee_name), employee_df in employee_groups:
        # Skip if employee info is missing
        if pd.isna(employee_id) or pd.isna(employee_name):
            logger.debug(f"Skipping employee with missing ID or name: {employee_id}, {employee_name}")
            continue
        
        # Debug: Log employee details
        max_hours = employee_df[FileColumns.FACILITY_TOTAL_HOURS].max()
        logger.debug(f"Processing employee: {employee_name} ({employee_id}) - Max daily hours: {max_hours}")
        
        try:
            # Calculate overtime for this employee
            overtime_stats = calculate_employee_overtime(employee_df, str(employee_id), str(employee_name))
            
            if overtime_stats:
                logger.debug(f"Employee {employee_name} has {overtime_stats['total_overtime_hours']:.2f} overtime hours")
                employee_overtime_data.append(overtime_stats)
                total_facility_overtime += overtime_stats['total_overtime_hours']
            else:
                logger.debug(f"Employee {employee_name} has no overtime")
        except Exception as e:
            logger.warning(f"Error calculating overtime for employee {employee_name} ({employee_id}): {str(e)}")
            continue
    
    # Sort employees by total overtime hours (descending)
    employee_overtime_data.sort(key=lambda x: x['total_overtime_hours'], reverse=True)
    
    # Create top N overtime employees list
    top_employees = []
    for rank, emp_data in enumerate(employee_overtime_data[:top_count], 1):
        # Convert role to short display name for reporting
        try:
            display_role = get_short_display_name(emp_data['primary_role'])
        except KeyError:
            logger.warning(f"No short display name found for role '{emp_data['primary_role']}', using original")
            display_role = emp_data['primary_role']
        
        overtime_employee = OvertimeEmployee(
            employee_id=emp_data['employee_id'],
            employee_name=emp_data['employee_name'],
            total_overtime_hours=emp_data['total_overtime_hours'],
            days_with_overtime=emp_data['days_with_overtime'],
            average_daily_overtime=emp_data['average_daily_overtime'],
            primary_role=display_role,
            rank=rank
        )
        top_employees.append(overtime_employee)
    
    logger.info(f"Overtime analysis complete: {len(employee_overtime_data)} employees with overtime, "
                f"{total_facility_overtime:.2f} total facility overtime hours")
    
    return OvertimeAnalysis(
        facility=facility_name,
        top_employees=top_employees,
        total_employees_with_overtime=len(employee_overtime_data),
        top_count_requested=top_count,
        total_overtime_hours_facility=total_facility_overtime,
        analysis_period_start=analysis_start_date,
        analysis_period_end=analysis_end_date
    )


def get_overtime_summary_statistics(overtime_analysis: OvertimeAnalysis) -> Dict[str, float]:
    """
    Calculate summary statistics from overtime analysis results.
    
    Args:
        overtime_analysis: OvertimeAnalysis object
        
    Returns:
        Dictionary with summary statistics
    """
    if not overtime_analysis.top_employees:
        return {
            'average_overtime_per_employee': 0.0,
            'highest_individual_overtime': 0.0,
            'average_days_with_overtime': 0.0,
            'overtime_concentration_ratio': 0.0  # Top N vs total facility overtime
        }
    
    # Calculate statistics from top employees (representative sample)
    total_top_overtime = sum(emp.total_overtime_hours for emp in overtime_analysis.top_employees)
    total_top_days = sum(emp.days_with_overtime for emp in overtime_analysis.top_employees)
    
    highest_overtime = max(emp.total_overtime_hours for emp in overtime_analysis.top_employees)
    average_overtime = total_top_overtime / len(overtime_analysis.top_employees)
    average_days = total_top_days / len(overtime_analysis.top_employees)
    
    # Calculate concentration ratio (what % of total facility overtime is from top N employees)
    concentration_ratio = 0.0
    if overtime_analysis.total_overtime_hours_facility > 0:
        concentration_ratio = (total_top_overtime / overtime_analysis.total_overtime_hours_facility) * 100
    
    return {
        'average_overtime_per_employee': average_overtime,
        'highest_individual_overtime': highest_overtime,
        'average_days_with_overtime': average_days,
        'overtime_concentration_ratio': concentration_ratio
    }


def validate_overtime_data(facility_df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    Validate that facility data contains required columns for overtime analysis.
    
    Args:
        facility_df: Facility hours DataFrame
        
    Returns:
        Tuple of (is_valid: bool, missing_columns: List[str])
    """
    required_columns = [
        FileColumns.FACILITY_EMPLOYEE_ID,
        FileColumns.FACILITY_EMPLOYEE_NAME,
        FileColumns.FACILITY_TOTAL_HOURS,
        FileColumns.FACILITY_STAFF_ROLE_NAME,
        FileColumns.FACILITY_HOURS_DATE
    ]
    
    missing_columns = [col for col in required_columns if col not in facility_df.columns]
    
    is_valid = len(missing_columns) == 0
    
    if not is_valid:
        logger.error(f"Missing required columns for overtime analysis: {missing_columns}")
    
    return is_valid, missing_columns


def analyze_overtime_by_role(facility_df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    """
    Analyze overtime patterns by role for additional insights.
    
    Args:
        facility_df: Facility hours DataFrame
        
    Returns:
        Dictionary mapping role names to overtime statistics
    """
    role_overtime_stats = defaultdict(lambda: {
        'total_overtime': 0.0,
        'employee_count': 0,
        'total_employees_with_overtime': 0,
        'average_overtime_per_employee': 0.0
    })
    
    # Group by employee and role to calculate individual overtime
    employee_groups = facility_df.groupby([
        FileColumns.FACILITY_EMPLOYEE_ID, 
        FileColumns.FACILITY_EMPLOYEE_NAME
    ])
    
    for (employee_id, employee_name), employee_df in employee_groups:
        if pd.isna(employee_id) or pd.isna(employee_name):
            continue
        
        primary_role = get_employee_primary_role(employee_df)
        overtime_stats = calculate_employee_overtime(employee_df, str(employee_id), str(employee_name))
        
        role_stats = role_overtime_stats[primary_role]
        role_stats['employee_count'] += 1
        
        if overtime_stats:
            role_stats['total_overtime'] += overtime_stats['total_overtime_hours']
            role_stats['total_employees_with_overtime'] += 1
    
    # Calculate averages
    for role, stats in role_overtime_stats.items():
        if stats['employee_count'] > 0:
            stats['average_overtime_per_employee'] = stats['total_overtime'] / stats['employee_count']
    
    return dict(role_overtime_stats)


# Initialize logging for this module
logger.info("Overtime analysis module initialized")