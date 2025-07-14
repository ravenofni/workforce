"""
Date range calculation utilities for workforce analytics.
Implements F-0 control variables for dynamic date range determination.
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Tuple, Optional
import logging

from config.constants import DATE_FORMAT, DayOfWeek
from config.settings import ControlVariables


logger = logging.getLogger(__name__)


def calculate_analysis_date_range(
    facility_df: pd.DataFrame,
    control_variables: ControlVariables,
    start_date_override: Optional[str] = None,
    end_date_override: Optional[str] = None
) -> Tuple[datetime, datetime]:
    """
    Calculate analysis date range using F-0 control variables and override logic.
    
    This function implements a 2-tier priority system for production safety:
    1. Command line/function parameters (highest priority) - for specific analysis periods
    2. Dynamic calculation using control variables (production default) - automatic calculation
    
    Note: For development testing, use VS Code launch.json configurations to pass
    specific date ranges as command line arguments, eliminating the need for constants.
    
    Args:
        facility_df: DataFrame with facility hours data
        control_variables: F-0 control variables
        start_date_override: Optional start date override (YYYY-MM-DD format)
        end_date_override: Optional end date override (YYYY-MM-DD format)
        
    Returns:
        Tuple of (analysis_start_date, analysis_end_date)
    """
    logger.info("Calculating analysis date range")
    
    # Priority 1: Command line/function parameters (highest priority)
    if start_date_override and end_date_override:
        logger.info("Using command line date overrides")
        start_date = datetime.strptime(start_date_override, "%Y-%m-%d")
        end_date = datetime.strptime(end_date_override, "%Y-%m-%d")
        return start_date, end_date
    
    # Priority 2: Dynamic calculation using control variables (production default)
    logger.info("Using dynamic date calculation with F-0 control variables")
    
    if facility_df.empty:
        logger.warning("Empty facility data - using current date")
        current_date = datetime.now()
        return current_date, current_date
    
    # Get the date column name
    from config.constants import FileColumns
    date_col = FileColumns.FACILITY_HOURS_DATE
    
    if date_col not in facility_df.columns:
        logger.error(f"Date column '{date_col}' not found in facility data")
        current_date = datetime.now()
        return current_date, current_date
    
    # Get the most recent date in the data
    most_recent_date = facility_df[date_col].max()
    logger.info(f"Most recent date in data: {most_recent_date.strftime(DATE_FORMAT)}")
    
    # Calculate period end date using F-0 control variables
    if control_variables.use_data_day:
        # F-0c & F-0d: Use new data day logic
        period_end_date = _find_most_recent_data_day(
            facility_df, date_col, control_variables.new_data_day
        )
        logger.info(f"Using new data day logic - period end: {period_end_date.strftime(DATE_FORMAT)}")
    else:
        # F-0a: Use days to drop logic
        period_end_date = most_recent_date - timedelta(days=control_variables.days_to_drop)
        logger.info(f"Using days to drop logic - period end: {period_end_date.strftime(DATE_FORMAT)}")
    
    # F-0b: Calculate analysis start date using days to process
    # Reason: Subtract (days_to_process - 1) to ensure the period includes exactly days_to_process days
    # Example: 84 days means 83 days back + end date = 84 total days in the analysis period
    analysis_start_date = period_end_date - timedelta(days=control_variables.days_to_process - 1)
    analysis_end_date = period_end_date
    
    logger.info(f"Calculated analysis period: {analysis_start_date.strftime(DATE_FORMAT)} to {analysis_end_date.strftime(DATE_FORMAT)}")
    logger.info(f"Analysis period span: {control_variables.days_to_process} days")
    
    return analysis_start_date, analysis_end_date


def _find_most_recent_data_day(facility_df: pd.DataFrame, date_col: str, target_day: int) -> datetime:
    """
    Find the most recent date that falls on the specified day of week.
    
    Args:
        facility_df: DataFrame with facility data
        date_col: Name of date column
        target_day: Target day of week (1=Sunday, 2=Monday, etc.)
        
    Returns:
        Most recent date matching the target day
    """
    # Reason: Convert from upstream Sunday=1 convention to Python's Monday=0 convention
    # This mapping ensures compatibility between F-0c NEW_DATA_DAY values and pandas datetime operations
    # Sunday=1 -> Python Sunday=6
    # Monday=2 -> Python Monday=0, etc.
    if target_day == 1:  # Sunday
        python_target_day = 6
    else:
        python_target_day = target_day - 2
    
    # Filter dates that match the target day of week
    matching_dates = facility_df[
        facility_df[date_col].dt.weekday == python_target_day
    ]
    
    if matching_dates.empty:
        logger.warning(f"No dates found for target day {target_day}, using most recent date")
        return facility_df[date_col].max()
    
    most_recent_matching = matching_dates[date_col].max()
    logger.info(f"Found most recent {DayOfWeek(target_day).name}: {most_recent_matching.strftime(DATE_FORMAT)}")
    
    return most_recent_matching


def validate_date_range(start_date: datetime, end_date: datetime) -> bool:
    """
    Validate that the date range is logical.
    
    Args:
        start_date: Analysis start date
        end_date: Analysis end date
        
    Returns:
        True if valid, False otherwise
    """
    if start_date >= end_date:
        logger.error(f"Invalid date range: start_date ({start_date.strftime(DATE_FORMAT)}) must be before end_date ({end_date.strftime(DATE_FORMAT)})")
        return False
    
    # Check if range is reasonable (not too long or too short)
    days_span = (end_date - start_date).days
    if days_span < 1:
        logger.error(f"Date range too short: {days_span} days")
        return False
    
    if days_span > 365:
        logger.warning(f"Date range very long: {days_span} days")
    
    return True