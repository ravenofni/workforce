"""
Facility hours data ingestion (F-2) - Load actual hours from CSV files.
Supports multi-facility CSV files separated by location key.
"""

import os
import pandas as pd
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, timedelta

from config.constants import (
    FACILITY_REQUIRED_COLUMNS,
    DATE_FORMAT,
    FileColumns
)
from src.models.data_models import FacilityHours, DataQualityException


logger = logging.getLogger(__name__)


def load_facility_data(file_path: str) -> tuple[pd.DataFrame, List[DataQualityException]]:
    """
    Load actual hours data from facility CSV file (F-2).
    Supports multi-facility data separated by location key.
    
    Args:
        file_path: Path to the facility data CSV file
        
    Returns:
        Tuple of (Validated DataFrame with facility hours data, List of data quality exceptions)
        
    Raises:
        FileNotFoundError: If facility data file not found
        ValueError: If required columns are missing or data is invalid
    """
    # PATTERN: File existence check from examples/data_processing.py:30
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Facility data file not found: {file_path}")
    
    logger.info(f"Loading facility data from: {file_path}")
    
    try:
        # PATTERN: CSV loading with column validation
        df = pd.read_csv(file_path)
        logger.info(f"Loaded {len(df)} rows from facility data file")
        
        # CRITICAL: Validate all required columns exist
        missing_cols = [col for col in FACILITY_REQUIRED_COLUMNS if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns in facility data: {missing_cols}")
        
        # Use original column names - no mapping needed
        
        # Data type conversions and validation
        df[FileColumns.FACILITY_TOTAL_HOURS] = pd.to_numeric(df[FileColumns.FACILITY_TOTAL_HOURS], errors='coerce')
        
        # Handle date parsing with flexible format handling (CRITICAL: Support both MMDDYY and MMDDYYYY)
        # Store original date column before conversion
        original_date_col = df[FileColumns.FACILITY_HOURS_DATE].copy()
        
        # Try the configured format first
        df[FileColumns.FACILITY_HOURS_DATE] = pd.to_datetime(df[FileColumns.FACILITY_HOURS_DATE], format=DATE_FORMAT, errors='coerce')
        
        # If most/all dates failed with the explicit format, try automatic parsing
        failed_dates = df[FileColumns.FACILITY_HOURS_DATE].isnull().sum()
        if failed_dates > len(df) * 0.5:  # If more than 50% failed
            logger.warning(f"Date format {DATE_FORMAT} failed for {failed_dates}/{len(df)} rows, trying automatic parsing")
            df[FileColumns.FACILITY_HOURS_DATE] = pd.to_datetime(original_date_col, errors='coerce')
        
        # Capture rows with invalid data as exceptions instead of dropping them
        initial_rows = len(df)
        data_quality_exceptions = []
        
        # Check for missing values in critical columns and create exceptions
        critical_columns = [FileColumns.FACILITY_TOTAL_HOURS, FileColumns.FACILITY_LOCATION_NAME, FileColumns.FACILITY_STAFF_ROLE_NAME, FileColumns.FACILITY_HOURS_DATE]
        for col in critical_columns:
            null_mask = df[col].isnull()
            null_count = null_mask.sum()
            
            if null_count > 0:
                logger.warning(f"Found {null_count} null values in {col} column - capturing as data quality exceptions")
                
                # Create exceptions for null values
                for idx in df[null_mask].index:
                    row = df.loc[idx]
                    exception = DataQualityException(
                        row_index=idx,
                        facility=row.get(FileColumns.FACILITY_LOCATION_NAME, None) if pd.notna(row.get(FileColumns.FACILITY_LOCATION_NAME, None)) else None,
                        role=row.get(FileColumns.FACILITY_STAFF_ROLE_NAME, None) if pd.notna(row.get(FileColumns.FACILITY_STAFF_ROLE_NAME, None)) else None,
                        employee_id=str(row.get(FileColumns.FACILITY_EMPLOYEE_ID, '')) if pd.notna(row.get(FileColumns.FACILITY_EMPLOYEE_ID, None)) else None,
                        issue_type='missing_required_field',
                        field_name=col,
                        original_value=None,
                        corrected_value="0" if col == FileColumns.FACILITY_TOTAL_HOURS else "Unknown",
                        severity='high' if col in [FileColumns.FACILITY_HOURS_DATE, FileColumns.FACILITY_TOTAL_HOURS] else 'medium',
                        description=f"Required field '{col}' is missing or null",
                        suggested_action=f"Verify data source provides valid {col} values for all records"
                    )
                    data_quality_exceptions.append(exception)
                
                # Fill null values to allow processing to continue
                if col == FileColumns.FACILITY_TOTAL_HOURS:
                    df.loc[null_mask, col] = 0.0
                elif col in [FileColumns.FACILITY_LOCATION_NAME, FileColumns.FACILITY_STAFF_ROLE_NAME]:
                    df.loc[null_mask, col] = 'Unknown'
                elif col == FileColumns.FACILITY_HOURS_DATE:
                    # Keep Date as NaT for now, will be handled in normalization
                    pass
        
        logger.info(f"Processed {initial_rows} records, captured {len(data_quality_exceptions)} data quality issues")
        
        # Handle negative hours
        negative_hours = df[FileColumns.FACILITY_TOTAL_HOURS] < 0
        if negative_hours.any():
            negative_count = negative_hours.sum()
            logger.warning(f"Found {negative_count} rows with negative actual hours - capturing as data quality exceptions")
            
            # Create exceptions for negative hours
            for idx in df[negative_hours].index:
                row = df.loc[idx]
                original_val = df.loc[idx, FileColumns.FACILITY_TOTAL_HOURS]
                exception = DataQualityException(
                    row_index=idx,
                    facility=row.get(FileColumns.FACILITY_LOCATION_NAME, None),
                    role=row.get(FileColumns.FACILITY_STAFF_ROLE_NAME, None),
                    employee_id=str(row.get(FileColumns.FACILITY_EMPLOYEE_ID, '')) if pd.notna(row.get(FileColumns.FACILITY_EMPLOYEE_ID, None)) else None,
                    issue_type='negative_hours',
                    field_name=FileColumns.FACILITY_TOTAL_HOURS,
                    original_value=str(original_val),
                    corrected_value="0.0",
                    severity='medium',
                    description=f"Negative hours value {original_val} found, corrected to 0",
                    suggested_action="Review data source for negative hour entries and correct at source"
                )
                data_quality_exceptions.append(exception)
            
            # Set negative values to 0
            df.loc[negative_hours, FileColumns.FACILITY_TOTAL_HOURS] = 0
        
        # Round hours to 2 decimal places
        df[FileColumns.FACILITY_TOTAL_HOURS] = df[FileColumns.FACILITY_TOTAL_HOURS].round(2)
        
        # Clean string columns
        df[FileColumns.FACILITY_LOCATION_NAME] = df[FileColumns.FACILITY_LOCATION_NAME].astype(str).str.strip()
        df[FileColumns.FACILITY_STAFF_ROLE_NAME] = df[FileColumns.FACILITY_STAFF_ROLE_NAME].astype(str).str.strip()
        
        if FileColumns.FACILITY_EMPLOYEE_ID in df.columns:
            df[FileColumns.FACILITY_EMPLOYEE_ID] = df[FileColumns.FACILITY_EMPLOYEE_ID].astype(str).str.strip()
        if FileColumns.FACILITY_EMPLOYEE_NAME in df.columns:
            df[FileColumns.FACILITY_EMPLOYEE_NAME] = df[FileColumns.FACILITY_EMPLOYEE_NAME].astype(str).str.strip()
        
        # Add day of week column for variance analysis
        if FileColumns.FACILITY_HOURS_DATE in df.columns:
            # Calculate day of week from date - use the same format as model data
            df[FileColumns.FACILITY_DAY_OF_WEEK] = df[FileColumns.FACILITY_HOURS_DATE].dt.strftime('%A')
            logger.info(f"Added day of week column for variance analysis")
        
        # Add weekly aggregation column (PATTERN: from examples line 85-108)
        df = add_weekly_aggregation(df)
        
        logger.info(f"Successfully processed {len(df)} facility data records")
        
        # Safe date range logging with NaT handling
        min_date = df[FileColumns.FACILITY_HOURS_DATE].min()
        max_date = df[FileColumns.FACILITY_HOURS_DATE].max()
        
        if pd.isna(min_date) or pd.isna(max_date):
            logger.warning("Date range contains NaT values - some dates could not be parsed")
            valid_dates = df[FileColumns.FACILITY_HOURS_DATE].dropna()
            if not valid_dates.empty:
                logger.info(f"Valid dates span {valid_dates.min().strftime(DATE_FORMAT)} to {valid_dates.max().strftime(DATE_FORMAT)}")
            else:
                logger.warning("No valid dates found in facility data")
        else:
            logger.info(f"Data spans {min_date.strftime(DATE_FORMAT)} to {max_date.strftime(DATE_FORMAT)}")
        
        return df, data_quality_exceptions
        
    except Exception as e:
        logger.error(f"Error loading facility data: {str(e)}")
        raise


def add_weekly_aggregation(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add weekly aggregation column (WeekStart) following examples pattern.
    Mirrors examples/data_processing.py get_week_start function.
    
    Args:
        df: DataFrame with facility data
        
    Returns:
        DataFrame with WeekStart column added
    """
    def get_week_start(date):
        """
        Given a pandas Timestamp, return the date of the Sunday for that week.
        Updated to use Sunday=1 convention matching upstream data.
        """
        # Convert Python weekday (Mon=0, Sun=6) to Sunday=1 convention
        # Python: Mon=0, Tue=1, Wed=2, Thu=3, Fri=4, Sat=5, Sun=6
        # Target: Sun=1, Mon=2, Tue=3, Wed=4, Thu=5, Fri=6, Sat=7
        python_weekday = date.weekday()
        if python_weekday == 6:  # Sunday in Python
            return date  # Already Sunday
        else:
            # Days to subtract to get to Sunday (always go backwards)
            days_to_subtract = python_weekday + 1
            return date - pd.Timedelta(days=days_to_subtract)
    
    df = df.copy()
    df['WeekStart'] = df[FileColumns.FACILITY_HOURS_DATE].apply(get_week_start)
    
    return df


def aggregate_to_weekly(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate daily data to weekly sums (Sunday-Saturday) for each Facility-Role.
    Mirrors examples/data_processing.py aggregate_to_weekly function.
    
    Args:
        df: DataFrame with daily facility data
        
    Returns:
        DataFrame aggregated to weekly level
    """
    df = df.copy()
    
    # Define aggregation columns
    agg_cols = [FileColumns.FACILITY_TOTAL_HOURS]
    group_cols = [FileColumns.FACILITY_LOCATION_NAME, FileColumns.FACILITY_STAFF_ROLE_NAME, 'WeekStart']
    
    # Only sum columns that exist in the DataFrame
    sum_cols = [col for col in agg_cols if col in df.columns]
    
    # Aggregate to weekly level
    weekly_df = df.groupby(group_cols)[sum_cols].sum().reset_index()
    
    # Merge in additional columns for sorting/grouping
    merge_cols = [FileColumns.FACILITY_LOCATION_NAME, FileColumns.FACILITY_STAFF_ROLE_NAME, FileColumns.FACILITY_LOCATION_KEY]
    if FileColumns.FACILITY_COST_CENTER_SORT in df.columns:
        merge_cols.append(FileColumns.FACILITY_COST_CENTER_SORT)
    if FileColumns.FACILITY_WORKFORCE_MODEL_ROLE_SORT in df.columns:
        merge_cols.append(FileColumns.FACILITY_WORKFORCE_MODEL_ROLE_SORT)
    
    available_merge_cols = [col for col in merge_cols if col in df.columns]
    if available_merge_cols:
        weekly_df = weekly_df.merge(
            df[available_merge_cols].drop_duplicates(),
            on=[FileColumns.FACILITY_LOCATION_NAME, FileColumns.FACILITY_STAFF_ROLE_NAME],
            how='left'
        )
    
    logger.info(f"Aggregated {len(df)} daily records to {len(weekly_df)} weekly records")
    
    return weekly_df


def get_facilities_summary(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Get summary statistics for facility data.
    
    Args:
        df: DataFrame with facility data
        
    Returns:
        Dictionary with summary statistics
    """
    if df.empty:
        return {
            'total_facilities': 0,
            'total_roles': 0,
            'total_actual_hours': 0.0,
            'date_range_start': None,
            'date_range_end': None,
            'records_count': 0
        }
    
    return {
        'total_facilities': df[FileColumns.FACILITY_LOCATION_NAME].nunique(),
        'total_roles': df[FileColumns.FACILITY_STAFF_ROLE_NAME].nunique(),
        'total_actual_hours': float(df[FileColumns.FACILITY_TOTAL_HOURS].sum()),
        'date_range_start': df[FileColumns.FACILITY_HOURS_DATE].min(),
        'date_range_end': df[FileColumns.FACILITY_HOURS_DATE].max(),
        'records_count': len(df),
        'facilities': sorted(df[FileColumns.FACILITY_LOCATION_NAME].unique().tolist()),
        'unique_employees': df[FileColumns.FACILITY_EMPLOYEE_ID].nunique() if FileColumns.FACILITY_EMPLOYEE_ID in df.columns else 0
    }


def separate_facilities(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """
    Separate multi-facility data by facility location key.
    
    Args:
        df: DataFrame with facility data for multiple facilities
        
    Returns:
        Dictionary mapping facility names to their data
    """
    facilities = {}
    
    for facility in df[FileColumns.FACILITY_LOCATION_NAME].unique():
        facility_data = df[df[FileColumns.FACILITY_LOCATION_NAME] == facility].copy()
        facilities[facility] = facility_data
        logger.debug(f"Facility '{facility}': {len(facility_data)} records")
    
    logger.info(f"Separated data for {len(facilities)} facilities")
    return facilities


def validate_facility_data(df: pd.DataFrame) -> List[str]:
    """
    Validate facility data for completeness and consistency.
    
    Args:
        df: DataFrame with facility data to validate
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    if df.empty:
        errors.append("Facility data is empty")
        return errors
    
    # Check for required columns
    required_cols = [FileColumns.FACILITY_LOCATION_NAME, FileColumns.FACILITY_STAFF_ROLE_NAME, FileColumns.FACILITY_TOTAL_HOURS, FileColumns.FACILITY_HOURS_DATE]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        errors.append(f"Missing required columns: {missing_cols}")
    
    # Check for null values in critical columns
    for col in required_cols:
        if col in df.columns:
            null_count = df[col].isnull().sum()
            if null_count > 0:
                errors.append(f"Found {null_count} null values in {col} column")
    
    # Check for negative hours
    if FileColumns.FACILITY_TOTAL_HOURS in df.columns:
        negative_hours = (df[FileColumns.FACILITY_TOTAL_HOURS] < 0).sum()
        if negative_hours > 0:
            errors.append(f"Found {negative_hours} records with negative actual hours")
    
    # Check date range validity
    if FileColumns.FACILITY_HOURS_DATE in df.columns and not df[FileColumns.FACILITY_HOURS_DATE].isnull().all():
        date_range = df[FileColumns.FACILITY_HOURS_DATE].max() - df[FileColumns.FACILITY_HOURS_DATE].min()
        if date_range.days > 730:  # More than 2 years
            errors.append(f"Date range spans {date_range.days} days, which may be excessive")
    
    return errors


def filter_data_by_date_range(df: pd.DataFrame, start_date: Optional[datetime] = None, 
                             end_date: Optional[datetime] = None) -> pd.DataFrame:
    """
    Filter facility data by date range.
    
    Args:
        df: DataFrame with facility data
        start_date: Start date for filtering (inclusive)
        end_date: End date for filtering (inclusive)
        
    Returns:
        Filtered DataFrame
    """
    filtered_df = df.copy()
    
    if start_date is not None:
        filtered_df = filtered_df[filtered_df[FileColumns.FACILITY_HOURS_DATE] >= start_date]
        logger.info(f"Filtered data from {start_date.strftime(DATE_FORMAT)} onwards")
    
    if end_date is not None:
        filtered_df = filtered_df[filtered_df[FileColumns.FACILITY_HOURS_DATE] <= end_date]
        logger.info(f"Filtered data up to {end_date.strftime(DATE_FORMAT)}")
    
    logger.info(f"Date filtering resulted in {len(filtered_df)} records")
    return filtered_df


def get_facility_role_combinations(df: pd.DataFrame) -> List[Dict[str, str]]:
    """
    Get all unique facility-role combinations in the data.
    
    Args:
        df: DataFrame with facility data
        
    Returns:
        List of dictionaries with facility and role combinations
    """
    combinations = df[[FileColumns.FACILITY_LOCATION_NAME, FileColumns.FACILITY_STAFF_ROLE_NAME]].drop_duplicates()
    return combinations.to_dict('records')