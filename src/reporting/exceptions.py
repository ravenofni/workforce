"""
Exception compiler (F-5) - Aggregate flags into a tidy "exceptions" DataFrame ready for reporting.
Compiles all types of exceptions into structured format for PDF report generation.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from config.constants import VarianceType, DATE_FORMAT, FileColumns
from src.models.data_models import (
    VarianceResult, 
    TrendAnalysisResult, 
    ExceptionSummary, 
    FacilityKPI
)


logger = logging.getLogger(__name__)


def _safe_date_range_format(date_series: pd.Series) -> str:
    """
    Safely format date range handling NaT values.
    
    Args:
        date_series: Pandas Series with dates
        
    Returns:
        Formatted date range string or 'N/A' if no valid dates
    """
    try:
        min_date = date_series.min()
        max_date = date_series.max()
        
        if pd.isna(min_date) or pd.isna(max_date):
            valid_dates = date_series.dropna()
            if not valid_dates.empty:
                return f"{valid_dates.min().strftime(DATE_FORMAT)} to {valid_dates.max().strftime(DATE_FORMAT)}"
            else:
                return "N/A"
        else:
            return f"{min_date.strftime(DATE_FORMAT)} to {max_date.strftime(DATE_FORMAT)}"
    except Exception:
        return "N/A"


def compile_exceptions(variances: List[VarianceResult], 
                      trend_results: List[TrendAnalysisResult] = None) -> pd.DataFrame:
    """
    Aggregate all exception flags into a tidy DataFrame ready for reporting (F-5).
    
    Args:
        variances: List of VarianceResult objects from variance detection
        trend_results: Optional list of TrendAnalysisResult objects
        
    Returns:
        Tidy DataFrame with all exceptions ready for reporting
    """
    if not variances and not trend_results:
        logger.warning("No variances or trend results provided for exception compilation")
        return pd.DataFrame()
    
    logger.info(f"Compiling exceptions from {len(variances)} variances and "
               f"{len(trend_results) if trend_results else 0} trend results")
    
    exceptions_data = []
    
    # Process variance exceptions
    for variance in variances:
        if variance.is_exception:
            exception_record = {
                'facility': variance.facility,
                'role': variance.role,
                'date': variance.date,
                'exception_type': variance.variance_type.value,
                'severity': _calculate_variance_severity(variance),
                'description': _generate_variance_description(variance),
                'variance_value': variance.variance_value,
                'variance_percentage': variance.variance_percentage,
                'threshold_used': variance.threshold_used,
                'model_hours': variance.model_hours,
                'actual_hours': variance.actual_hours,
                'control_limit_violated': variance.control_limit_violated,
                'source': 'variance_detection'
            }
            exceptions_data.append(exception_record)
    
    # Process trend exceptions if provided
    if trend_results:
        trend_exceptions = [t for t in trend_results if t.is_significant_trend and 
                          t.trend_direction in ['increasing', 'decreasing']]
        
        for trend in trend_exceptions:
            exception_record = {
                'facility': trend.facility,
                'role': trend.role,
                'date': trend.analysis_end_date,
                'exception_type': 'trend',
                'severity': _calculate_trend_severity(trend),
                'description': _generate_trend_description(trend),
                'variance_value': trend.slope,
                'variance_percentage': None,
                'threshold_used': 0.05,  # Standard p-value threshold
                'model_hours': None,
                'actual_hours': None,
                'control_limit_violated': f"Significant {trend.trend_direction} trend",
                'source': 'trend_analysis'
            }
            exceptions_data.append(exception_record)
    
    # Convert to DataFrame
    if not exceptions_data:
        logger.info("No exceptions found to compile")
        return pd.DataFrame()
    
    exceptions_df = pd.DataFrame(exceptions_data)
    
    # Sort by facility, severity (descending), and date
    exceptions_df = exceptions_df.sort_values(
        ['facility', 'severity', 'date'], 
        ascending=[True, False, False]
    ).reset_index(drop=True)
    
    logger.info(f"Compiled {len(exceptions_df)} exceptions into tidy DataFrame")
    
    return exceptions_df


def _calculate_variance_severity(variance: VarianceResult) -> float:
    """
    Calculate severity score for a variance (0-100 scale).
    
    Args:
        variance: VarianceResult object
        
    Returns:
        Severity score (0-100)
    """
    if variance.variance_type == VarianceType.MODEL:
        # Model variance severity based on percentage deviation
        if variance.variance_percentage is not None:
            return min(abs(variance.variance_percentage), 100.0)
        else:
            return 50.0  # Default moderate severity
    
    elif variance.variance_type == VarianceType.STATISTICAL:
        # Statistical variance severity based on magnitude of violation
        if variance.variance_value is not None:
            # Normalize to 0-100 scale (arbitrary but consistent)
            return min(abs(variance.variance_value) * 10, 100.0)
        else:
            return 60.0  # Default moderate-high severity
    
    else:  # TREND
        return 70.0  # Trend exceptions are generally serious


def _calculate_trend_severity(trend: TrendAnalysisResult) -> float:
    """
    Calculate severity score for a trend (0-100 scale).
    
    Args:
        trend: TrendAnalysisResult object
        
    Returns:
        Severity score (0-100)
    """
    # Base severity on statistical significance (lower p-value = higher severity)
    base_severity = (1 - trend.p_value) * 100
    
    # Adjust based on R-squared (better fit = higher confidence in trend)
    r_squared_adjustment = trend.r_squared * 20
    
    # Combine scores
    severity = min(base_severity + r_squared_adjustment, 100.0)
    
    return round(severity, 2)


def _generate_variance_description(variance: VarianceResult) -> str:
    """
    Generate human-readable description for a variance exception.
    
    Args:
        variance: VarianceResult object
        
    Returns:
        Human-readable description string
    """
    if variance.variance_type == VarianceType.MODEL:
        if variance.variance_percentage is not None:
            direction = "above" if variance.variance_percentage > 0 else "below"
            return (f"Actual hours {direction} model by {abs(variance.variance_percentage):.1f}% "
                   f"(threshold: {variance.threshold_used}%)")
        else:
            return "Variance from model hours detected"
    
    elif variance.variance_type == VarianceType.STATISTICAL:
        return f"Statistical control limit violation: {variance.control_limit_violated}"
    
    elif variance.variance_type == VarianceType.TREND:
        return f"Significant trend detected: {variance.control_limit_violated}"
    
    else:
        return "Exception detected"


def _generate_trend_description(trend: TrendAnalysisResult) -> str:
    """
    Generate human-readable description for a trend exception.
    
    Args:
        trend: TrendAnalysisResult object
        
    Returns:
        Human-readable description string
    """
    return (f"Significant {trend.trend_direction} trend over {trend.weeks_analyzed} weeks "
           f"(p-value: {trend.p_value:.4f}, R²: {trend.r_squared:.3f})")


def filter_exceptions_by_facility(exceptions_df: pd.DataFrame, facility: str) -> pd.DataFrame:
    """
    Filter exceptions DataFrame for a specific facility.
    
    Args:
        exceptions_df: DataFrame with compiled exceptions
        facility: Facility name to filter by
        
    Returns:
        Filtered DataFrame containing only exceptions for the specified facility
    """
    if exceptions_df.empty:
        return exceptions_df
    
    return exceptions_df[exceptions_df['facility'] == facility].copy()


def filter_exceptions_by_severity(exceptions_df: pd.DataFrame, 
                                 min_severity: float = 50.0) -> pd.DataFrame:
    """
    Filter exceptions by minimum severity threshold.
    
    Args:
        exceptions_df: DataFrame with compiled exceptions
        min_severity: Minimum severity score to include
        
    Returns:
        Filtered DataFrame containing only exceptions above severity threshold
    """
    if exceptions_df.empty:
        return exceptions_df
    
    return exceptions_df[exceptions_df['severity'] >= min_severity].copy()


def calculate_period_model_hours(model_data: pd.DataFrame, 
                                 facility: str,
                                 analysis_start_date: datetime, 
                                 analysis_end_date: datetime) -> float:
    """
    Calculate expected model hours for a specific facility and time period using actual calendar days.
    
    Args:
        model_data: DataFrame with model hours data
        facility: Facility name
        analysis_start_date: Start date of analysis period
        analysis_end_date: End date of analysis period
        
    Returns:
        Total expected model hours for the period
    """
    from datetime import timedelta
    
    if model_data.empty:
        return 0.0
    
    # Filter model data for this facility
    facility_model = model_data[model_data[FileColumns.MODEL_LOCATION_NAME] == facility] if FileColumns.MODEL_LOCATION_NAME in model_data.columns else pd.DataFrame()
    
    if facility_model.empty:
        logger.warning(f"No model data found for facility: {facility}")
        return 0.0
    
    # Iterate through each actual calendar day in the analysis period
    current_date = analysis_start_date
    total_period_hours = 0.0
    days_processed = 0
    
    while current_date <= analysis_end_date:
        # Convert Python weekday to model DAY_NUMBER convention
        # Python: Monday=0, Tuesday=1, ..., Sunday=6
        # Model: Sunday=1, Monday=2, Tuesday=3, ..., Saturday=7
        python_weekday = current_date.weekday()  # 0=Monday, 6=Sunday
        model_day_number = (python_weekday + 2) % 7  # Convert to model convention
        if model_day_number == 0:  # Handle Sunday case
            model_day_number = 7
        
        # Get model hours for this specific day of week
        day_model_hours = facility_model[
            facility_model[FileColumns.MODEL_DAY_NUMBER] == model_day_number
        ][FileColumns.MODEL_TOTAL_HOURS].sum()
        
        total_period_hours += day_model_hours
        days_processed += 1
        
        # Move to next day
        current_date += timedelta(days=1)
        
        # Safety check to prevent infinite loops
        if days_processed > 400:  # More than a year worth of days
            logger.error(f"Period model calculation exceeded safety limit for {facility}")
            break
    
    logger.debug(f"Period model calculation for {facility}: {days_processed} actual calendar days = {total_period_hours:.2f} total hours")
    
    return total_period_hours


def generate_facility_exception_summary(exceptions_df: pd.DataFrame, 
                                       facility: str) -> ExceptionSummary:
    """
    Generate exception summary for a specific facility.
    
    Args:
        exceptions_df: DataFrame with compiled exceptions
        facility: Facility name
        
    Returns:
        ExceptionSummary object with aggregated statistics
    """
    facility_exceptions = filter_exceptions_by_facility(exceptions_df, facility)
    
    if facility_exceptions.empty:
        # Return empty summary
        return ExceptionSummary(
            facility=facility,
            analysis_period_start=datetime.now(),
            analysis_period_end=datetime.now(),
            total_exceptions=0,
            model_variances=0,
            statistical_exceptions=0,
            trend_exceptions=0,
            roles_with_exceptions=[],
            severity_score=0.0
        )
    
    # Calculate summary statistics
    total_exceptions = len(facility_exceptions)
    model_variances = len(facility_exceptions[facility_exceptions['exception_type'] == 'model'])
    statistical_exceptions = len(facility_exceptions[facility_exceptions['exception_type'] == 'statistical'])
    trend_exceptions = len(facility_exceptions[facility_exceptions['exception_type'] == 'trend'])
    
    roles_with_exceptions = facility_exceptions['role'].unique().tolist()
    
    # Calculate overall severity score (weighted average)
    severity_score = facility_exceptions['severity'].mean() if total_exceptions > 0 else 0.0
    
    # Determine analysis period
    analysis_start = facility_exceptions['date'].min()
    analysis_end = facility_exceptions['date'].max()
    
    return ExceptionSummary(
        facility=facility,
        analysis_period_start=analysis_start,
        analysis_period_end=analysis_end,
        total_exceptions=total_exceptions,
        model_variances=model_variances,
        statistical_exceptions=statistical_exceptions,
        trend_exceptions=trend_exceptions,
        roles_with_exceptions=roles_with_exceptions,
        severity_score=severity_score
    )


def calculate_facility_kpis(exceptions_df: pd.DataFrame, 
                          facility_data: pd.DataFrame,
                          model_data: pd.DataFrame,
                          facility: str,
                          analysis_start_date: datetime,
                          analysis_end_date: datetime) -> FacilityKPI:
    """
    Calculate Key Performance Indicators for a facility.
    
    Args:
        exceptions_df: DataFrame with compiled exceptions
        facility_data: DataFrame with facility hours data
        model_data: DataFrame with model hours data
        facility: Facility name
        analysis_start_date: Start date of analysis period
        analysis_end_date: End date of analysis period
        
    Returns:
        FacilityKPI object with calculated metrics
    """
    # Filter data for this facility
    facility_hours = facility_data[facility_data[FileColumns.FACILITY_LOCATION_NAME] == facility]
    facility_model = model_data[model_data[FileColumns.MODEL_LOCATION_NAME] == facility] if FileColumns.MODEL_LOCATION_NAME in model_data.columns else pd.DataFrame()
    facility_exceptions = filter_exceptions_by_facility(exceptions_df, facility)
    
    # Calculate basic metrics
    total_actual_hours = facility_hours[FileColumns.FACILITY_TOTAL_HOURS].sum() if not facility_hours.empty else 0.0
    
    # Calculate period-specific model hours instead of total model hours
    total_model_hours = calculate_period_model_hours(
        model_data, facility, analysis_start_date, analysis_end_date
    )
    
    # Calculate variance percentage
    if total_model_hours > 0:
        variance_percentage = ((total_actual_hours - total_model_hours) / total_model_hours) * 100
    else:
        variance_percentage = 0.0
    
    # Role analysis
    roles_analyzed = facility_hours[FileColumns.FACILITY_STAFF_ROLE_NAME].nunique() if not facility_hours.empty else 0
    roles_with_exceptions = facility_exceptions['role'].nunique() if not facility_exceptions.empty else 0
    
    # Exception rate
    exception_rate = (roles_with_exceptions / roles_analyzed * 100) if roles_analyzed > 0 else 0.0
    
    # Variance statistics
    if not facility_exceptions.empty:
        role_variances = facility_exceptions.groupby('role')['variance_percentage'].mean()
        average_variance = role_variances.mean() if not role_variances.empty else 0.0
        largest_variance = role_variances.abs().max() if not role_variances.empty else 0.0
        most_problematic_role = role_variances.abs().idxmax() if not role_variances.empty else None
    else:
        average_variance = 0.0
        largest_variance = 0.0
        most_problematic_role = None
    
    return FacilityKPI(
        facility=facility,
        total_model_hours=total_model_hours,
        total_actual_hours=total_actual_hours,
        variance_percentage=variance_percentage,
        roles_analyzed=roles_analyzed,
        roles_with_exceptions=roles_with_exceptions,
        exception_rate=exception_rate,
        average_variance=average_variance,
        largest_variance=largest_variance,
        most_problematic_role=most_problematic_role
    )


def generate_exceptions_summary_table(exceptions_df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate summary table of exceptions by facility for display.
    
    Args:
        exceptions_df: DataFrame with compiled exceptions
        
    Returns:
        Summary DataFrame suitable for display
    """
    if exceptions_df.empty:
        return pd.DataFrame()
    
    # Group by facility and calculate summary statistics
    summary_data = []
    
    for facility in exceptions_df['facility'].unique():
        facility_exceptions = filter_exceptions_by_facility(exceptions_df, facility)
        
        summary_record = {
            'Facility': facility,
            'Total_Exceptions': len(facility_exceptions),
            'Model_Variances': len(facility_exceptions[facility_exceptions['exception_type'] == 'model']),
            'Statistical_Exceptions': len(facility_exceptions[facility_exceptions['exception_type'] == 'statistical']),
            'Trend_Exceptions': len(facility_exceptions[facility_exceptions['exception_type'] == 'trend']),
            'Roles_Affected': facility_exceptions['role'].nunique(),
            'Avg_Severity': facility_exceptions['severity'].mean(),
            'Max_Severity': facility_exceptions['severity'].max(),
            'Date_Range': _safe_date_range_format(facility_exceptions['date'])
        }
        summary_data.append(summary_record)
    
    summary_df = pd.DataFrame(summary_data)
    
    # Sort by total exceptions (descending)
    summary_df = summary_df.sort_values('Total_Exceptions', ascending=False).reset_index(drop=True)
    
    return summary_df


def display_exceptions_summary(exceptions_df: pd.DataFrame) -> None:
    """
    Display a formatted summary of compiled exceptions.
    
    Args:
        exceptions_df: DataFrame with compiled exceptions
    """
    if exceptions_df.empty:
        print("No exceptions found to display.")
        return
    
    print("\n" + "="*100)
    print("EXCEPTION COMPILATION SUMMARY (F-5)")
    print("="*100)
    
    # Overall statistics
    total_exceptions = len(exceptions_df)
    unique_facilities = exceptions_df['facility'].nunique()
    unique_roles = exceptions_df['role'].nunique()
    
    model_count = len(exceptions_df[exceptions_df['exception_type'] == 'model'])
    statistical_count = len(exceptions_df[exceptions_df['exception_type'] == 'statistical'])
    trend_count = len(exceptions_df[exceptions_df['exception_type'] == 'trend'])
    
    print(f"Total Exceptions: {total_exceptions}")
    print(f"Facilities Affected: {unique_facilities}")
    print(f"Roles Affected: {unique_roles}")
    print(f"Average Severity: {exceptions_df['severity'].mean():.1f}")
    print()
    
    print("Exception Breakdown by Type:")
    print(f"  Model Variances: {model_count} ({model_count/total_exceptions*100:.1f}%)")
    print(f"  Statistical Exceptions: {statistical_count} ({statistical_count/total_exceptions*100:.1f}%)")
    print(f"  Trend Exceptions: {trend_count} ({trend_count/total_exceptions*100:.1f}%)")
    print()
    
    # Summary table by facility
    summary_df = generate_exceptions_summary_table(exceptions_df)
    
    print("Exceptions by Facility:")
    print("-" * 100)
    print(f"{'Facility':<20} {'Total':<8} {'Model':<8} {'Statistical':<12} {'Trend':<8} {'Roles':<8} {'Avg Sev':<8}")
    print("-" * 100)
    
    for _, row in summary_df.iterrows():
        print(f"{row['Facility']:<20} {row['Total_Exceptions']:<8} {row['Model_Variances']:<8} "
              f"{row['Statistical_Exceptions']:<12} {row['Trend_Exceptions']:<8} "
              f"{row['Roles_Affected']:<8} {row['Avg_Severity']:<8.1f}")
    
    print("="*100 + "\n")


def export_exceptions_to_csv(exceptions_df: pd.DataFrame, file_path: str) -> None:
    """
    Export compiled exceptions to CSV file.
    
    Args:
        exceptions_df: DataFrame with compiled exceptions
        file_path: Path where CSV file should be saved
    """
    try:
        exceptions_df.to_csv(file_path, index=False)
        logger.info(f"Exported {len(exceptions_df)} exceptions to {file_path}")
    except Exception as e:
        logger.error(f"Error exporting exceptions to CSV: {str(e)}")
        raise