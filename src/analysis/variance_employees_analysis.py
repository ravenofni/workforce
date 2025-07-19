"""
Variance Employees Analysis Module for Workforce Analytics.

This module calculates variance hours for employees based on role-specific model hours.
It identifies employees who worked more than their expected model hours and provides
ranking and analysis for reporting.

The system:
- Uses role-specific model hours from the role display mapper
- Calculates daily variance by comparing actual hours to model hours
- Aggregates variance across the analysis period
- Provides ranking and statistical analysis of variance patterns
- Supports configurable top-N reporting

Example Usage:
    from src.analysis.variance_employees_analysis import calculate_variance_employees_analysis
    
    # Calculate top 5 variance employees for a facility
    variance_result = calculate_variance_employees_analysis(
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

from src.models.data_models import VarianceEmployee, VarianceEmployeesAnalysis, VarianceFunctionGroup
from src.utils.role_display_mapper import get_standard_shift_hours, get_short_display_name, get_role_function, get_dynamic_shift_hours
from config.constants import FileColumns

logger = logging.getLogger(__name__)


def calculate_daily_variance(actual_hours: float, model_hours: float) -> float:
    """
    Calculate variance hours for a single day.
    
    Args:
        actual_hours: Hours actually worked
        model_hours: Expected hours from the model for the role
        
    Returns:
        Variance hours (0.0 if no variance)
    """
    if actual_hours <= model_hours:
        return 0.0
    return actual_hours - model_hours


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


def calculate_employee_variance(employee_df: pd.DataFrame, 
                              employee_id: str, 
                              employee_name: str,
                              model_data: Optional[pd.DataFrame] = None,
                              facility: Optional[str] = None,
                              role_shift_hours_cache: Optional[Dict[str, float]] = None) -> Optional[Dict]:
    """
    Calculate variance statistics for a single employee.
    
    Args:
        employee_df: DataFrame containing all records for the employee
        employee_id: Employee identifier
        employee_name: Employee name
        model_data: Optional DataFrame with model data for dynamic shift hours
        facility: Optional facility name for facility-specific model data
        role_shift_hours_cache: Optional pre-calculated role hours cache for performance
        
    Returns:
        Dictionary with variance statistics or None if no variance
    """
    if employee_df.empty:
        return None
    
    # Filter out NULL/NaN roles and unmapped categories for variance calculation
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
    
    # Calculate role-specific variance for each work record
    total_variance_hours = 0.0
    days_with_variance = 0
    
    for _, row in valid_work_df.iterrows():
        role = row[FileColumns.FACILITY_STAFF_ROLE_NAME]
        actual_hours = row[FileColumns.FACILITY_TOTAL_HOURS]
        
        # Get shift hours for THIS specific role (use cache if available for performance)
        try:
            if role_shift_hours_cache and role in role_shift_hours_cache:
                # Use pre-calculated hours from cache for performance
                role_standard_hours = role_shift_hours_cache[role]
                logger.debug(f"Employee {employee_name} worked {actual_hours} hours as {role} (cached standard: {role_standard_hours})")
            else:
                # Fallback to dynamic lookup (slower but comprehensive)
                role_standard_hours = get_dynamic_shift_hours(role, model_data, facility)
                logger.debug(f"Employee {employee_name} worked {actual_hours} hours as {role} (dynamic standard: {role_standard_hours})")
        except KeyError:
            logger.warning(f"No shift hours found for role '{role}', skipping record")
            continue
        
        # Skip unmapped roles (they have 0.0 standard hours)
        if role_standard_hours == 0.0:
            logger.debug(f"Skipping unmapped/unknown role '{role}' for variance calculation")
            continue
        
        # Calculate variance for this specific role/day
        daily_variance = calculate_daily_variance(actual_hours, role_standard_hours)
        
        if daily_variance > 0:
            total_variance_hours += daily_variance
            days_with_variance += 1
            logger.debug(f"Employee {employee_name} had {daily_variance:.2f} variance hours as {role}")
    
    # Only return data if employee has variance
    if total_variance_hours <= 0:
        return None
    
    # Calculate average daily variance (only for days with variance)
    average_daily_variance = total_variance_hours / max(days_with_variance, 1)
    
    return {
        'employee_id': employee_id,
        'employee_name': employee_name,
        'total_variance_hours': total_variance_hours,
        'days_with_variance': days_with_variance,
        'average_daily_variance': average_daily_variance,
        'primary_role': primary_role
    }


def calculate_variance_employees_analysis(facility_df: pd.DataFrame,
                              facility_name: str,
                              analysis_start_date: datetime,
                              analysis_end_date: datetime,
                              top_count: int = 3,
                              model_data: Optional[pd.DataFrame] = None) -> VarianceEmployeesAnalysis:
    """
    Calculate variance employees analysis for a facility.
    
    Args:
        facility_df: DataFrame with facility hours data (already filtered by date)
        facility_name: Name of the facility
        analysis_start_date: Start date of analysis period
        analysis_end_date: End date of analysis period
        top_count: Number of top variance employees to include
        model_data: Optional DataFrame with model data for dynamic shift hours
        
    Returns:
        VarianceEmployeesAnalysis object with top employees and summary statistics
    """
    logger.info(f"Calculating variance employees analysis for {facility_name} from {analysis_start_date} to {analysis_end_date}")
    
    # Pre-calculate role shift hours to avoid repeated DataFrame operations
    role_shift_hours_cache = {}
    if model_data is not None and not model_data.empty:
        from src.utils.role_display_mapper import get_role_shift_hours_by_facility
        try:
            role_shift_hours_cache = get_role_shift_hours_by_facility(model_data, facility_name)
            logger.debug(f"Pre-calculated shift hours for {len(role_shift_hours_cache)} roles from model data")
        except Exception as e:
            logger.warning(f"Error pre-calculating role shift hours: {e}, will use static mappings")
    
    # Debug: Log details about the facility data received
    logger.debug(f"Facility DataFrame shape: {facility_df.shape}")
    if not facility_df.empty:
        logger.debug(f"Facility DataFrame columns: {list(facility_df.columns)}")
        logger.debug(f"Unique facilities in data: {facility_df[FileColumns.FACILITY_LOCATION_NAME].unique() if FileColumns.FACILITY_LOCATION_NAME in facility_df.columns else 'NO FACILITY COLUMN'}")
        high_hours = facility_df[facility_df[FileColumns.FACILITY_TOTAL_HOURS] > 8.0] if FileColumns.FACILITY_TOTAL_HOURS in facility_df.columns else pd.DataFrame()
        logger.debug(f"Records with > 8 hours: {len(high_hours)}")
    
    if facility_df.empty:
        logger.warning(f"No facility data provided for variance employees analysis: {facility_name}")
        return VarianceEmployeesAnalysis(
            facility=facility_name,
            top_employees=[],
            total_employees_with_variance=0,
            top_count_requested=top_count,
            total_variance_hours_facility=0.0,
            analysis_period_start=analysis_start_date,
            analysis_period_end=analysis_end_date
        )
    
    # Group by employee to calculate individual variance
    employee_variance_data = []
    total_facility_variance = 0.0
    
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
            # Calculate variance for this employee using cached role hours for performance
            variance_stats = calculate_employee_variance(employee_df, str(employee_id), str(employee_name), model_data, facility_name, role_shift_hours_cache)
            
            if variance_stats:
                logger.debug(f"Employee {employee_name} has {variance_stats['total_variance_hours']:.2f} variance hours")
                employee_variance_data.append(variance_stats)
                total_facility_variance += variance_stats['total_variance_hours']
            else:
                logger.debug(f"Employee {employee_name} has no variance")
        except Exception as e:
            logger.warning(f"Error calculating variance for employee {employee_name} ({employee_id}): {str(e)}")
            continue
    
    # Sort employees by total variance hours (descending)
    employee_variance_data.sort(key=lambda x: x['total_variance_hours'], reverse=True)
    
    # Group employees by function (clinical vs non-clinical)
    clinical_employees = []
    non_clinical_employees = []
    
    for emp_data in employee_variance_data:
        # Determine function of the employee's primary role
        try:
            role_function = get_role_function(emp_data['primary_role'])
            logger.debug(f"Employee {emp_data['employee_name']} primary role '{emp_data['primary_role']}' classified as: {role_function}")
        except KeyError:
            logger.warning(f"No function found for role '{emp_data['primary_role']}', defaulting to non-clinical")
            role_function = "non-clinical"
        except Exception as e:
            logger.error(f"Error getting function for role '{emp_data['primary_role']}': {str(e)}, defaulting to non-clinical")
            role_function = "non-clinical"
        
        # Convert role to short display name for reporting
        try:
            display_role = get_short_display_name(emp_data['primary_role'])
        except KeyError:
            logger.warning(f"No short display name found for role '{emp_data['primary_role']}', using original")
            display_role = emp_data['primary_role']
        
        # Create VarianceEmployee object
        variance_employee = VarianceEmployee(
            employee_id=emp_data['employee_id'],
            employee_name=emp_data['employee_name'],
            total_variance_hours=emp_data['total_variance_hours'],
            days_with_variance=emp_data['days_with_variance'],
            average_daily_variance=emp_data['average_daily_variance'],
            primary_role=display_role,
            rank=1  # Will be set properly when creating function groups
        )
        
        # Group by function
        if role_function == "clinical":
            clinical_employees.append(variance_employee)
        else:
            non_clinical_employees.append(variance_employee)
    
    # Create function groups with top N employees each
    clinical_group = None
    non_clinical_group = None
    
    if clinical_employees:
        # Set ranks for clinical employees
        for rank, emp in enumerate(clinical_employees[:top_count], 1):
            emp.rank = rank
        
        clinical_total_hours = sum(emp.total_variance_hours for emp in clinical_employees)
        clinical_group = VarianceFunctionGroup(
            function="clinical",
            display_name="Clinical Associates",
            employees=clinical_employees[:top_count],
            total_variance_hours=clinical_total_hours,
            total_employees_in_function=len(clinical_employees)
        )
    
    if non_clinical_employees:
        # Set ranks for non-clinical employees
        for rank, emp in enumerate(non_clinical_employees[:top_count], 1):
            emp.rank = rank
        
        non_clinical_total_hours = sum(emp.total_variance_hours for emp in non_clinical_employees)
        non_clinical_group = VarianceFunctionGroup(
            function="non-clinical",
            display_name="Non-Clinical Associates",
            employees=non_clinical_employees[:top_count],
            total_variance_hours=non_clinical_total_hours,
            total_employees_in_function=len(non_clinical_employees)
        )
    
    # Create legacy top N list (for backward compatibility)
    top_employees = []
    for rank, emp_data in enumerate(employee_variance_data[:top_count], 1):
        try:
            display_role = get_short_display_name(emp_data['primary_role'])
        except KeyError:
            display_role = emp_data['primary_role']
        
        variance_employee = VarianceEmployee(
            employee_id=emp_data['employee_id'],
            employee_name=emp_data['employee_name'],
            total_variance_hours=emp_data['total_variance_hours'],
            days_with_variance=emp_data['days_with_variance'],
            average_daily_variance=emp_data['average_daily_variance'],
            primary_role=display_role,
            rank=rank
        )
        top_employees.append(variance_employee)
    
    logger.info(f"Variance employees analysis complete: {len(employee_variance_data)} employees with variance, "
                f"{total_facility_variance:.2f} total facility variance hours")
    logger.info(f"Clinical employees with variance: {len(clinical_employees)}, "
                f"Non-clinical employees with variance: {len(non_clinical_employees)}")
    logger.info(f"Clinical group created: {clinical_group is not None}, Non-clinical group created: {non_clinical_group is not None}")
    
    return VarianceEmployeesAnalysis(
        facility=facility_name,
        top_employees=top_employees,
        clinical_group=clinical_group,
        non_clinical_group=non_clinical_group,
        total_employees_with_variance=len(employee_variance_data),
        top_count_requested=top_count,
        total_variance_hours_facility=total_facility_variance,
        analysis_period_start=analysis_start_date,
        analysis_period_end=analysis_end_date
    )


def get_variance_summary_statistics(variance_analysis: VarianceEmployeesAnalysis) -> Dict[str, float]:
    """
    Calculate summary statistics from variance employees analysis results.
    
    Args:
        variance_analysis: VarianceEmployeesAnalysis object
        
    Returns:
        Dictionary with summary statistics
    """
    if not variance_analysis.top_employees:
        return {
            'average_variance_per_employee': 0.0,
            'highest_individual_variance': 0.0,
            'average_days_with_variance': 0.0,
            'variance_concentration_ratio': 0.0  # Top N vs total facility variance
        }
    
    # Calculate statistics from top employees (representative sample)
    total_top_variance = sum(emp.total_variance_hours for emp in variance_analysis.top_employees)
    total_top_days = sum(emp.days_with_variance for emp in variance_analysis.top_employees)
    
    highest_variance = max(emp.total_variance_hours for emp in variance_analysis.top_employees)
    average_variance = total_top_variance / len(variance_analysis.top_employees)
    average_days = total_top_days / len(variance_analysis.top_employees)
    
    # Calculate concentration ratio (what % of total facility variance is from top N employees)
    concentration_ratio = 0.0
    if variance_analysis.total_variance_hours_facility > 0:
        concentration_ratio = (total_top_variance / variance_analysis.total_variance_hours_facility) * 100
    
    return {
        'average_variance_per_employee': average_variance,
        'highest_individual_variance': highest_variance,
        'average_days_with_variance': average_days,
        'variance_concentration_ratio': concentration_ratio
    }


def validate_variance_data(facility_df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    Validate that facility data contains required columns for variance employees analysis.
    
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
        logger.error(f"Missing required columns for variance employees analysis: {missing_columns}")
    
    return is_valid, missing_columns


def analyze_variance_by_role(facility_df: pd.DataFrame, 
                            model_data: Optional[pd.DataFrame] = None,
                            facility_name: Optional[str] = None,
                            role_shift_hours_cache: Optional[Dict[str, float]] = None) -> Dict[str, Dict[str, float]]:
    """
    Analyze variance patterns by role for additional insights.
    
    Args:
        facility_df: Facility hours DataFrame
        model_data: Optional DataFrame with model data for dynamic shift hours
        facility_name: Optional facility name for facility-specific model data
        role_shift_hours_cache: Optional pre-calculated role hours cache for performance
        
    Returns:
        Dictionary mapping role names to variance statistics
    """
    role_variance_stats = defaultdict(lambda: {
        'total_variance': 0.0,
        'employee_count': 0,
        'total_employees_with_variance': 0,
        'average_variance_per_employee': 0.0
    })
    
    # Group by employee and role to calculate individual variance
    employee_groups = facility_df.groupby([
        FileColumns.FACILITY_EMPLOYEE_ID, 
        FileColumns.FACILITY_EMPLOYEE_NAME
    ])
    
    for (employee_id, employee_name), employee_df in employee_groups:
        if pd.isna(employee_id) or pd.isna(employee_name):
            continue
        
        primary_role = get_employee_primary_role(employee_df)
        variance_stats = calculate_employee_variance(employee_df, str(employee_id), str(employee_name), model_data, facility_name, role_shift_hours_cache)
        
        role_stats = role_variance_stats[primary_role]
        role_stats['employee_count'] += 1
        
        if variance_stats:
            role_stats['total_variance'] += variance_stats['total_variance_hours']
            role_stats['total_employees_with_variance'] += 1
    
    # Calculate averages
    for role, stats in role_variance_stats.items():
        if stats['employee_count'] > 0:
            stats['average_variance_per_employee'] = stats['total_variance'] / stats['employee_count']
    
    return dict(role_variance_stats)


# Initialize logging for this module
logger.info("Variance employees analysis module initialized")