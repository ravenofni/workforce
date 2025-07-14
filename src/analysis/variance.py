"""
Variance detection (F-3a, F-3b) - Detect statistical variances and model deviations.
Implements variance detection for Role × Day × Facility and Employee × Role combinations.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from config.constants import VarianceType, DEFAULT_VARIANCE_THRESHOLD, FileColumns
from config.settings import ControlVariables
from src.models.data_models import VarianceResult, StatisticalSummary
from src.analysis.statistics import calculate_control_limits, detect_control_violations
from src.ingestion.model_loader import get_model_hours_for_facility_role, get_model_hours_for_facility_role_day


logger = logging.getLogger(__name__)


def detect_model_variances(df: pd.DataFrame, model_df: pd.DataFrame, 
                          control_vars: ControlVariables) -> List[VarianceResult]:
    """
    Detect variances from model hours (F-0f implementation).
    
    Args:
        df: DataFrame with actual hours data
        model_df: DataFrame with model hours data
        control_vars: Control variables including variance threshold
        
    Returns:
        List of VarianceResult objects for model variances
    """
    variances = []
    
    if df.empty or model_df.empty:
        logger.warning("Empty DataFrame(s) provided for model variance detection")
        return variances
    
    logger.info(f"Detecting model variances with threshold {control_vars.variance_threshold}%")
    
    # Group by facility, role, AND day of week for proper model comparison
    grouped = df.groupby([FileColumns.FACILITY_LOCATION_NAME, FileColumns.FACILITY_STAFF_ROLE_NAME, FileColumns.FACILITY_DAY_OF_WEEK])
    
    for (facility, role, day_of_week), group in grouped:
        try:
            # Get model hours for this facility/role/day combination
            model_hours = get_model_hours_for_facility_role_day(model_df, facility, role, day_of_week)
            
            # Calculate mean actual hours for comparison
            actual_hours_mean = group[FileColumns.FACILITY_TOTAL_HOURS].mean()
            
            # Calculate percentage variance using utility function
            variance_percentage = calculate_variance_percentage(actual_hours_mean, model_hours)
            
            # Handle infinity case (when model hours = 0 but actual hours > 0)
            if variance_percentage == float('inf'):
                logger.debug(f"Model expects 0 hours for {facility} - {role} on {day_of_week}, but {actual_hours_mean:.2f} actual hours found - significant variance")
                # Use a large percentage that will always exceed threshold
                variance_percentage = 999.0  # Represents "infinite" variance for reporting
            elif model_hours == 0 and actual_hours_mean == 0:
                logger.debug(f"Both model and actual hours are 0 for {facility} - {role} on {day_of_week} - no variance")
            
            # Check if variance exceeds threshold
            is_exception = abs(variance_percentage) > control_vars.variance_threshold
            
            if is_exception:
                # Create variance result for each date in the group
                for _, row in group.iterrows():
                    variance = VarianceResult(
                        facility=facility,
                        role=role,
                        date=row[FileColumns.FACILITY_HOURS_DATE],
                        variance_type=VarianceType.MODEL,
                        variance_value=float(actual_hours_mean - model_hours),
                        variance_percentage=round(variance_percentage, 2),
                        is_exception=True,
                        threshold_used=control_vars.variance_threshold,
                        model_hours=model_hours,
                        actual_hours=float(row[FileColumns.FACILITY_TOTAL_HOURS])
                    )
                    variances.append(variance)
                
                logger.info(f"Model variance detected: {facility} - {role} on {day_of_week}: {variance_percentage:.2f}%")
        
        except Exception as e:
            logger.error(f"Error detecting model variance for {facility} - {role} on {day_of_week}: {str(e)}")
            continue
    
    logger.info(f"Detected {len(variances)} model variance exceptions")
    return variances


def detect_statistical_variances_by_role_day_facility(df: pd.DataFrame, 
                                                     control_vars: ControlVariables) -> List[VarianceResult]:
    """
    Detect statistical variances for each Role × Day × Facility combination (F-3a).
    
    Args:
        df: DataFrame with facility hours data
        control_vars: Control variables for statistical analysis
        
    Returns:
        List of VarianceResult objects for statistical variances
    """
    variances = []
    
    if df.empty or not control_vars.use_statistics:
        logger.info("Statistical variance detection disabled or no data available")
        return variances
    
    logger.info("Detecting statistical variances by Role × Day × Facility")
    
    # Group by facility and role for control limit calculation
    facility_role_groups = df.groupby([FileColumns.FACILITY_LOCATION_NAME, FileColumns.FACILITY_STAFF_ROLE_NAME])
    
    for (facility, role), group in facility_role_groups:
        try:
            actual_hours = group[FileColumns.FACILITY_TOTAL_HOURS].dropna()
            
            if len(actual_hours) < 3:
                logger.debug(f"Insufficient data for {facility} - {role} (n={len(actual_hours)})")
                continue
            
            # Calculate control limits for this facility/role combination
            control_limits = calculate_control_limits(actual_hours)
            
            # Detect violations for each day
            violations = detect_control_violations(actual_hours, control_limits)
            
            # Convert violations to VarianceResult objects
            for violation in violations:
                # Get the date for this violation
                violation_idx = violation['index']
                violation_row = group.loc[violation_idx]
                
                variance = VarianceResult(
                    facility=facility,
                    role=role,
                    date=violation_row[FileColumns.FACILITY_HOURS_DATE],
                    variance_type=VarianceType.STATISTICAL,
                    variance_value=violation['magnitude'],
                    variance_percentage=None,
                    is_exception=True,
                    threshold_used=None,
                    model_hours=None,
                    actual_hours=violation['value'],
                    control_limit_violated=f"{violation['violation_type']} control limit"
                )
                variances.append(variance)
            
            if violations:
                logger.info(f"Statistical variances detected: {facility} - {role}: {len(violations)} violations")
        
        except Exception as e:
            logger.error(f"Error detecting statistical variances for {facility} - {role}: {str(e)}")
            continue
    
    logger.info(f"Detected {len(variances)} statistical variance exceptions")
    return variances


def detect_statistical_variances_by_employee_role(df: pd.DataFrame, 
                                                 control_vars: ControlVariables) -> List[VarianceResult]:
    """
    Detect statistical variances for each Employee × Role combination (F-3b).
    
    Args:
        df: DataFrame with facility hours data including employee information
        control_vars: Control variables for statistical analysis
        
    Returns:
        List of VarianceResult objects for employee-level statistical variances
    """
    variances = []
    
    if df.empty or not control_vars.use_statistics:
        logger.info("Employee-level statistical variance detection disabled or no data available")
        return variances
    
    if FileColumns.FACILITY_EMPLOYEE_ID not in df.columns:
        logger.warning("EmployeeId column not found, skipping employee-level variance detection")
        return variances
    
    logger.info("Detecting statistical variances by Employee × Role")
    
    # Group by facility, employee, and role
    employee_groups = df.groupby([FileColumns.FACILITY_LOCATION_NAME, FileColumns.FACILITY_EMPLOYEE_ID, FileColumns.FACILITY_STAFF_ROLE_NAME])
    
    for (facility, employee_id, role), group in employee_groups:
        try:
            actual_hours = group[FileColumns.FACILITY_TOTAL_HOURS].dropna()
            
            if len(actual_hours) < 3:
                logger.debug(f"Insufficient data for {facility} - {employee_id} - {role} (n={len(actual_hours)})")
                continue
            
            # Calculate control limits for this employee/role combination
            control_limits = calculate_control_limits(actual_hours)
            
            # Detect violations for each work period
            violations = detect_control_violations(actual_hours, control_limits)
            
            # Convert violations to VarianceResult objects
            for violation in violations:
                violation_idx = violation['index']
                violation_row = group.loc[violation_idx]
                
                variance = VarianceResult(
                    facility=facility,
                    role=role,
                    date=violation_row[FileColumns.FACILITY_HOURS_DATE],
                    variance_type=VarianceType.STATISTICAL,
                    variance_value=violation['magnitude'],
                    variance_percentage=None,
                    is_exception=True,
                    threshold_used=None,
                    model_hours=None,
                    actual_hours=violation['value'],
                    control_limit_violated=f"{violation['violation_type']} control limit (employee-level)"
                )
                variances.append(variance)
            
            if violations:
                logger.info(f"Employee statistical variances: {facility} - {employee_id} - {role}: {len(violations)} violations")
        
        except Exception as e:
            logger.error(f"Error detecting employee variances for {facility} - {employee_id} - {role}: {str(e)}")
            continue
    
    logger.info(f"Detected {len(variances)} employee-level statistical variance exceptions")
    return variances


def detect_all_variances(df: pd.DataFrame, model_df: pd.DataFrame, 
                        control_vars: ControlVariables) -> List[VarianceResult]:
    """
    Detect all types of variances (model, statistical facility-level, statistical employee-level).
    
    Args:
        df: DataFrame with facility hours data
        model_df: DataFrame with model hours data
        control_vars: Control variables for analysis
        
    Returns:
        Combined list of all VarianceResult objects
    """
    logger.info("Starting comprehensive variance detection")
    
    all_variances = []
    
    # 1. Model variances (F-0f)
    model_variances = detect_model_variances(df, model_df, control_vars)
    all_variances.extend(model_variances)
    
    # 2. Statistical variances by Role × Day × Facility (F-3a)
    statistical_variances_facility = detect_statistical_variances_by_role_day_facility(df, control_vars)
    all_variances.extend(statistical_variances_facility)
    
    # 3. Statistical variances by Employee × Role (F-3b)
    statistical_variances_employee = detect_statistical_variances_by_employee_role(df, control_vars)
    all_variances.extend(statistical_variances_employee)
    
    # Summary logging
    variance_summary = {
        'model_variances': len(model_variances),
        'facility_statistical_variances': len(statistical_variances_facility),
        'employee_statistical_variances': len(statistical_variances_employee),
        'total_variances': len(all_variances)
    }
    
    logger.info(f"Variance detection complete: {variance_summary}")
    
    return all_variances


def calculate_variance_percentage(actual: float, expected: float) -> float:
    """
    Calculate percentage variance between actual and expected values.
    
    Args:
        actual: Actual value
        expected: Expected value
        
    Returns:
        Percentage variance
    """
    if expected == 0:
        return 0.0 if actual == 0 else float('inf')
    
    return ((actual - expected) / expected) * 100


def filter_variances_by_facility(variances: List[VarianceResult], facility: str) -> List[VarianceResult]:
    """
    Filter variance results for a specific facility.
    
    Args:
        variances: List of VarianceResult objects
        facility: Facility name to filter by
        
    Returns:
        Filtered list of variances for the specified facility
    """
    return [v for v in variances if v.facility == facility]


def filter_variances_by_type(variances: List[VarianceResult], variance_type: VarianceType) -> List[VarianceResult]:
    """
    Filter variance results by type.
    
    Args:
        variances: List of VarianceResult objects
        variance_type: Type of variance to filter by
        
    Returns:
        Filtered list of variances of the specified type
    """
    return [v for v in variances if v.variance_type == variance_type]


def get_variance_summary_by_facility(variances: List[VarianceResult]) -> Dict[str, Dict[str, int]]:
    """
    Get summary of variances grouped by facility.
    
    Args:
        variances: List of VarianceResult objects
        
    Returns:
        Dictionary with variance counts by facility and type
    """
    summary = {}
    
    for variance in variances:
        facility = variance.facility
        variance_type = variance.variance_type.value
        
        if facility not in summary:
            summary[facility] = {
                'model': 0,
                'statistical': 0,
                'trend': 0,
                'total': 0
            }
        
        summary[facility][variance_type] += 1
        summary[facility]['total'] += 1
    
    return summary


def get_most_problematic_roles(variances: List[VarianceResult]) -> List[Dict[str, Any]]:
    """
    Identify roles with the most variance exceptions.
    
    Args:
        variances: List of VarianceResult objects
        
    Returns:
        List of dictionaries with role variance statistics
    """
    role_counts = {}
    
    for variance in variances:
        key = f"{variance.facility} - {variance.role}"
        
        if key not in role_counts:
            role_counts[key] = {
                'facility': variance.facility,
                'role': variance.role,
                'total_exceptions': 0,
                'model_exceptions': 0,
                'statistical_exceptions': 0,
                'trend_exceptions': 0
            }
        
        role_counts[key]['total_exceptions'] += 1
        if variance.variance_type == VarianceType.MODEL:
            role_counts[key]['model_exceptions'] += 1
        elif variance.variance_type == VarianceType.STATISTICAL:
            role_counts[key]['statistical_exceptions'] += 1
        elif variance.variance_type == VarianceType.TREND:
            role_counts[key]['trend_exceptions'] += 1
    
    # Sort by total exceptions (descending)
    sorted_roles = sorted(role_counts.values(), key=lambda x: x['total_exceptions'], reverse=True)
    
    return sorted_roles


def display_variance_summary(variances: List[VarianceResult]) -> None:
    """
    Display a summary of detected variances.
    
    Args:
        variances: List of VarianceResult objects to summarize
    """
    if not variances:
        print("No variances detected.")
        return
    
    print("\n" + "="*80)
    print("VARIANCE DETECTION SUMMARY")
    print("="*80)
    
    # Overall summary
    total_variances = len(variances)
    model_count = len([v for v in variances if v.variance_type == VarianceType.MODEL])
    statistical_count = len([v for v in variances if v.variance_type == VarianceType.STATISTICAL])
    trend_count = len([v for v in variances if v.variance_type == VarianceType.TREND])
    
    print(f"Total Variances Detected: {total_variances}")
    print(f"  Model Variances: {model_count}")
    print(f"  Statistical Variances: {statistical_count}")
    print(f"  Trend Variances: {trend_count}")
    print()
    
    # Facility summary
    facility_summary = get_variance_summary_by_facility(variances)
    
    print("Variances by Facility:")
    print("-" * 60)
    print(f"{'Facility':<20} {'Model':<8} {'Statistical':<12} {'Trend':<8} {'Total':<8}")
    print("-" * 60)
    
    for facility, counts in sorted(facility_summary.items()):
        print(f"{facility:<20} {counts['model']:<8} {counts['statistical']:<12} {counts['trend']:<8} {counts['total']:<8}")
    
    print()
    
    # Most problematic roles
    problematic_roles = get_most_problematic_roles(variances)[:10]  # Top 10
    
    if problematic_roles:
        print("Most Problematic Roles (Top 10):")
        print("-" * 80)
        print(f"{'Facility':<20} {'Role':<25} {'Total':<8} {'Model':<8} {'Statistical':<12}")
        print("-" * 80)
        
        for role_info in problematic_roles:
            print(f"{role_info['facility']:<20} {role_info['role']:<25} "
                  f"{role_info['total_exceptions']:<8} {role_info['model_exceptions']:<8} "
                  f"{role_info['statistical_exceptions']:<12}")
    
    print("="*80 + "\n")