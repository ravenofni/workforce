"""
Trend analysis implementation (F-4) - Trailing window analysis with linear regression.
Detects trends using linear regression slope and p-value calculations.
"""

import pandas as pd
import numpy as np
from scipy import stats
from typing import List, Dict, Any, Optional, Tuple
import logging
from datetime import datetime, timedelta

from config.constants import VarianceType, FileColumns
from config.settings import ControlVariables
from src.models.data_models import TrendAnalysisResult, VarianceResult


logger = logging.getLogger(__name__)


def calculate_linear_trend(x_values: np.ndarray, y_values: np.ndarray) -> Tuple[float, float, float]:
    """
    Calculate linear regression trend statistics.
    
    Args:
        x_values: Independent variable (typically time/date numeric values)
        y_values: Dependent variable (actual hours)
        
    Returns:
        Tuple of (slope, p_value, r_squared)
    """
    if len(x_values) != len(y_values) or len(x_values) < 2:
        return 0.0, 1.0, 0.0
    
    try:
        # Perform linear regression
        slope, intercept, r_value, p_value, std_err = stats.linregress(x_values, y_values)
        r_squared = r_value ** 2
        
        return float(slope), float(p_value), float(r_squared)
        
    except Exception as e:
        logger.error(f"Error calculating linear trend: {str(e)}")
        return 0.0, 1.0, 0.0


def determine_trend_direction(slope: float, p_value: float, significance_threshold: float = 0.05) -> str:
    """
    Determine trend direction based on slope and statistical significance.
    
    Args:
        slope: Linear regression slope
        p_value: Statistical significance p-value
        significance_threshold: P-value threshold for significance
        
    Returns:
        Trend direction: 'increasing', 'decreasing', or 'stable'
    """
    if p_value > significance_threshold:
        return 'stable'
    
    if slope > 0:
        return 'increasing'
    elif slope < 0:
        return 'decreasing'
    else:
        return 'stable'


def analyze_facility_role_trend(df: pd.DataFrame, facility: str, role: str, 
                              weeks_for_trends: int) -> Optional[TrendAnalysisResult]:
    """
    Analyze trend for a specific facility-role combination.
    
    Args:
        df: DataFrame with facility hours data
        facility: Facility name
        role: Role name
        weeks_for_trends: Number of weeks to include in trend analysis
        
    Returns:
        TrendAnalysisResult object or None if insufficient data
    """
    # Filter data for this facility-role combination
    subset = df[(df[FileColumns.FACILITY_LOCATION_NAME] == facility) & (df[FileColumns.FACILITY_STAFF_ROLE_NAME] == role)].copy()
    
    if subset.empty:
        logger.debug(f"No data found for {facility} - {role}")
        return None
    
    # Sort by date and get recent data
    subset = subset.sort_values(FileColumns.FACILITY_HOURS_DATE)
    
    # Calculate cutoff date for trend analysis
    max_date = subset[FileColumns.FACILITY_HOURS_DATE].max()
    cutoff_date = max_date - timedelta(weeks=weeks_for_trends)
    trend_data = subset[subset[FileColumns.FACILITY_HOURS_DATE] >= cutoff_date].copy()
    
    if len(trend_data) < 3:
        logger.debug(f"Insufficient trend data for {facility} - {role} (n={len(trend_data)})")
        return None
    
    try:
        # Prepare data for linear regression
        # Convert dates to numeric values (days since first date)
        min_date = trend_data[FileColumns.FACILITY_HOURS_DATE].min()
        trend_data['days_from_start'] = (trend_data[FileColumns.FACILITY_HOURS_DATE] - min_date).dt.days
        
        # Group by week to reduce noise (use weekly aggregation if available)
        if 'WeekStart' in trend_data.columns:
            weekly_data = trend_data.groupby('WeekStart').agg({
                FileColumns.FACILITY_TOTAL_HOURS: 'mean',
                FileColumns.FACILITY_HOURS_DATE: 'first'
            }).reset_index()
            
            # Convert to days from start for regression
            weekly_data['days_from_start'] = (weekly_data[FileColumns.FACILITY_HOURS_DATE] - min_date).dt.days
            
            x_values = weekly_data['days_from_start'].values
            y_values = weekly_data[FileColumns.FACILITY_TOTAL_HOURS].values
        else:
            x_values = trend_data['days_from_start'].values
            y_values = trend_data[FileColumns.FACILITY_TOTAL_HOURS].values
        
        # Calculate trend statistics
        slope, p_value, r_squared = calculate_linear_trend(x_values, y_values)
        
        # Determine trend direction
        trend_direction = determine_trend_direction(slope, p_value)
        
        # Check if trend is statistically significant
        is_significant = p_value <= 0.05
        
        # Create result object
        result = TrendAnalysisResult(
            facility=facility,
            role=role,
            analysis_start_date=trend_data[FileColumns.FACILITY_HOURS_DATE].min(),
            analysis_end_date=trend_data[FileColumns.FACILITY_HOURS_DATE].max(),
            slope=round(slope, 4),
            p_value=round(p_value, 4),
            r_squared=round(r_squared, 4),
            is_significant_trend=is_significant,
            trend_direction=trend_direction,
            weeks_analyzed=weeks_for_trends
        )
        
        logger.debug(f"Trend analysis for {facility} - {role}: {trend_direction} "
                    f"(slope={slope:.4f}, p={p_value:.4f})")
        
        return result
        
    except Exception as e:
        logger.error(f"Error analyzing trend for {facility} - {role}: {str(e)}")
        return None


def analyze_trends_for_all_facilities(df: pd.DataFrame, 
                                    control_vars: ControlVariables) -> List[TrendAnalysisResult]:
    """
    Perform trend analysis for all facility-role combinations.
    
    Args:
        df: DataFrame with facility hours data
        control_vars: Control variables including weeks_for_trends
        
    Returns:
        List of TrendAnalysisResult objects
    """
    if df.empty:
        logger.warning("Empty DataFrame provided for trend analysis")
        return []
    
    logger.info(f"Starting trend analysis for {control_vars.weeks_for_trends} weeks")
    
    results = []
    
    # Get all unique facility-role combinations
    combinations = df[[FileColumns.FACILITY_LOCATION_NAME, FileColumns.FACILITY_STAFF_ROLE_NAME]].drop_duplicates()
    
    logger.info(f"Analyzing trends for {len(combinations)} facility-role combinations")
    
    for _, row in combinations.iterrows():
        facility = row[FileColumns.FACILITY_LOCATION_NAME]
        role = row[FileColumns.FACILITY_STAFF_ROLE_NAME]
        
        trend_result = analyze_facility_role_trend(df, facility, role, control_vars.weeks_for_trends)
        
        if trend_result:
            results.append(trend_result)
    
    logger.info(f"Completed trend analysis for {len(results)} facility-role combinations")
    
    return results


def detect_trend_exceptions(trend_results: List[TrendAnalysisResult], 
                           severity_threshold: float = 0.01) -> List[VarianceResult]:
    """
    Detect trend-based exceptions that may indicate variance issues.
    
    Args:
        trend_results: List of TrendAnalysisResult objects
        severity_threshold: P-value threshold for considering trends as exceptions
        
    Returns:
        List of VarianceResult objects for trend exceptions
    """
    exceptions = []
    
    logger.info(f"Detecting trend exceptions with p-value threshold {severity_threshold}")
    
    for trend in trend_results:
        try:
            # Consider significant trends with strong statistical evidence as exceptions
            is_exception = (trend.is_significant_trend and 
                          trend.p_value <= severity_threshold and
                          trend.trend_direction in ['increasing', 'decreasing'])
            
            if is_exception:
                # Create variance result for trend exception
                variance = VarianceResult(
                    facility=trend.facility,
                    role=trend.role,
                    date=trend.analysis_end_date,
                    variance_type=VarianceType.TREND,
                    variance_value=float(trend.slope),
                    variance_percentage=None,
                    is_exception=True,
                    threshold_used=severity_threshold,
                    model_hours=None,
                    actual_hours=None,
                    control_limit_violated=f"Significant {trend.trend_direction} trend"
                )
                
                exceptions.append(variance)
                
                logger.info(f"Trend exception detected: {trend.facility} - {trend.role} "
                           f"({trend.trend_direction} trend, p={trend.p_value:.4f})")
        
        except Exception as e:
            logger.error(f"Error detecting trend exception for {trend.facility} - {trend.role}: {str(e)}")
            continue
    
    logger.info(f"Detected {len(exceptions)} trend exceptions")
    return exceptions


def get_trend_summary_statistics(trend_results: List[TrendAnalysisResult]) -> Dict[str, Any]:
    """
    Generate summary statistics for trend analysis results.
    
    Args:
        trend_results: List of TrendAnalysisResult objects
        
    Returns:
        Dictionary with trend summary statistics
    """
    if not trend_results:
        return {
            'total_analyses': 0,
            'significant_trends': 0,
            'increasing_trends': 0,
            'decreasing_trends': 0,
            'stable_trends': 0,
            'average_r_squared': 0.0,
            'median_p_value': 0.0
        }
    
    significant_count = sum(1 for t in trend_results if t.is_significant_trend)
    increasing_count = sum(1 for t in trend_results if t.trend_direction == 'increasing')
    decreasing_count = sum(1 for t in trend_results if t.trend_direction == 'decreasing')
    stable_count = sum(1 for t in trend_results if t.trend_direction == 'stable')
    
    r_squared_values = [t.r_squared for t in trend_results]
    p_values = [t.p_value for t in trend_results]
    
    return {
        'total_analyses': len(trend_results),
        'significant_trends': significant_count,
        'increasing_trends': increasing_count,
        'decreasing_trends': decreasing_count,
        'stable_trends': stable_count,
        'average_r_squared': round(np.mean(r_squared_values), 4),
        'median_p_value': round(np.median(p_values), 4),
        'significance_rate': round(significant_count / len(trend_results) * 100, 2)
    }


def filter_trends_by_facility(trend_results: List[TrendAnalysisResult], 
                             facility: str) -> List[TrendAnalysisResult]:
    """
    Filter trend results for a specific facility.
    
    Args:
        trend_results: List of TrendAnalysisResult objects
        facility: Facility name to filter by
        
    Returns:
        Filtered list of trend results for the specified facility
    """
    return [t for t in trend_results if t.facility == facility]


def get_most_concerning_trends(trend_results: List[TrendAnalysisResult], 
                              limit: int = 10) -> List[TrendAnalysisResult]:
    """
    Get the most concerning trends based on statistical significance and direction.
    
    Args:
        trend_results: List of TrendAnalysisResult objects
        limit: Maximum number of trends to return
        
    Returns:
        List of most concerning trends, sorted by significance
    """
    # Filter for significant trends that are increasing or decreasing
    concerning_trends = [
        t for t in trend_results 
        if t.is_significant_trend and t.trend_direction in ['increasing', 'decreasing']
    ]
    
    # Sort by p-value (most significant first)
    concerning_trends.sort(key=lambda t: t.p_value)
    
    return concerning_trends[:limit]


def display_trend_summary(trend_results: List[TrendAnalysisResult]) -> None:
    """
    Display a summary of trend analysis results.
    
    Args:
        trend_results: List of TrendAnalysisResult objects to summarize
    """
    if not trend_results:
        print("No trend analysis results available.")
        return
    
    print("\n" + "="*80)
    print("TREND ANALYSIS SUMMARY")
    print("="*80)
    
    # Summary statistics
    summary = get_trend_summary_statistics(trend_results)
    
    print(f"Total Analyses: {summary['total_analyses']}")
    print(f"Significant Trends: {summary['significant_trends']} ({summary['significance_rate']:.1f}%)")
    print(f"  Increasing: {summary['increasing_trends']}")
    print(f"  Decreasing: {summary['decreasing_trends']}")
    print(f"  Stable: {summary['stable_trends']}")
    print(f"Average R-squared: {summary['average_r_squared']:.4f}")
    print(f"Median P-value: {summary['median_p_value']:.4f}")
    print()
    
    # Most concerning trends
    concerning_trends = get_most_concerning_trends(trend_results, 10)
    
    if concerning_trends:
        print("Most Concerning Trends:")
        print("-" * 80)
        print(f"{'Facility':<20} {'Role':<25} {'Direction':<12} {'P-value':<10} {'R²':<8}")
        print("-" * 80)
        
        for trend in concerning_trends:
            print(f"{trend.facility:<20} {trend.role:<25} {trend.trend_direction:<12} "
                  f"{trend.p_value:<10.4f} {trend.r_squared:<8.4f}")
    
    print("="*80 + "\n")


def generate_trend_data_for_facility(df: pd.DataFrame, facility: str, 
                                   weeks_for_trends: int) -> pd.DataFrame:
    """
    Generate trend data suitable for visualization for a specific facility.
    
    Args:
        df: DataFrame with facility hours data
        facility: Facility name
        weeks_for_trends: Number of weeks to include
        
    Returns:
        DataFrame with trend data for visualization
    """
    facility_data = df[df[FileColumns.FACILITY_LOCATION_NAME] == facility].copy()
    
    if facility_data.empty:
        return pd.DataFrame()
    
    # Filter to recent weeks
    max_date = facility_data[FileColumns.FACILITY_HOURS_DATE].max()
    cutoff_date = max_date - timedelta(weeks=weeks_for_trends)
    trend_data = facility_data[facility_data[FileColumns.FACILITY_HOURS_DATE] >= cutoff_date].copy()
    
    # Aggregate by week and role
    if 'WeekStart' in trend_data.columns:
        weekly_data = trend_data.groupby(['WeekStart', FileColumns.FACILITY_STAFF_ROLE_NAME]).agg({
            FileColumns.FACILITY_TOTAL_HOURS: 'mean'
        }).reset_index()
        
        return weekly_data
    else:
        # Daily aggregation if weekly not available
        daily_data = trend_data.groupby([FileColumns.FACILITY_HOURS_DATE, FileColumns.FACILITY_STAFF_ROLE_NAME]).agg({
            FileColumns.FACILITY_TOTAL_HOURS: 'mean'
        }).reset_index()
        
        return daily_data