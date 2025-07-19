"""
Model data ingestion (F-1) - Load model hours from CSV files.
Implements F-1a display requirement with formatted table output.
"""

import os
import pandas as pd
from typing import List, Dict, Any
import logging
from datetime import datetime

from config.constants import (
    MODEL_REQUIRED_COLUMNS,
    DATE_FORMAT,
    FileColumns,
    ComparisonType
)
from src.models.data_models import ModelHours, DataQualityException


logger = logging.getLogger(__name__)


def load_model_data(file_path: str) -> tuple[pd.DataFrame, List[DataQualityException]]:
    """
    Load and validate model hours data (F-1).
    
    Args:
        file_path: Path to the model data CSV file
        
    Returns:
        Tuple of (Validated DataFrame with model hours data, List of data quality exceptions)
        
    Raises:
        FileNotFoundError: If model data file not found
        ValueError: If required columns are missing or data is invalid
    """
    # PATTERN: File existence check from examples/data_processing.py:30
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Model data file not found: {file_path}")
    
    logger.info(f"Loading model data from: {file_path}")
    
    try:
        # PATTERN: CSV loading with column validation
        df = pd.read_csv(file_path)
        logger.info(f"Loaded {len(df)} rows from model data file")
        
        # Check for and handle row number column if present
        if FileColumns.MODEL_ROW_NUMBER in df.columns:
            logger.info("Detected row number column in model data - removing for processing")
            df = df.drop(columns=[FileColumns.MODEL_ROW_NUMBER])
        
        # Log new columns if present (for future use)
        new_columns = [
            FileColumns.MODEL_COMPANY_WORKDAY_ID,
            FileColumns.MODEL_LOCATION_WORKDAY_ID,
            FileColumns.MODEL_TOTAL_MINUTES,
            FileColumns.MODEL_WORKDAY_MODEL_WID,
            FileColumns.MODEL_COST_CENTER,
            FileColumns.MODEL_STAFF_COUNT,
            FileColumns.MODEL_DAILY_HOURS_PER_ROLE
        ]
        
        detected_new_columns = [col for col in new_columns if col in df.columns]
        if detected_new_columns:
            logger.info(f"Detected new model data columns: {detected_new_columns}")
            logger.info("These columns are available for future use but will not affect current processing")
        
        # CRITICAL: Validate all required columns exist
        missing_cols = [col for col in MODEL_REQUIRED_COLUMNS if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns in model data: {missing_cols}")
        
        # Use original column names - no mapping needed
        
        # Data type conversions and validation
        df[FileColumns.MODEL_TOTAL_HOURS] = pd.to_numeric(df[FileColumns.MODEL_TOTAL_HOURS], errors='coerce')
        
        # Skip date parsing for model data - we only need day of the week, not actual dates
        # Model data Date column (if present) is only used for reference and not for analysis
        
        # Capture rows with invalid data as exceptions instead of dropping them
        initial_rows = len(df)
        data_quality_exceptions = []
        
        # Check for missing values in critical columns and create exceptions
        critical_columns = [FileColumns.MODEL_TOTAL_HOURS, FileColumns.MODEL_LOCATION_NAME, FileColumns.MODEL_STAFF_ROLE_NAME]
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
                        facility=row.get(FileColumns.MODEL_LOCATION_NAME, None) if pd.notna(row.get(FileColumns.MODEL_LOCATION_NAME, None)) else None,
                        role=row.get(FileColumns.MODEL_STAFF_ROLE_NAME, None) if pd.notna(row.get(FileColumns.MODEL_STAFF_ROLE_NAME, None)) else None,
                        employee_id=None,  # Model data doesn't have employee IDs
                        issue_type='missing_required_field',
                        field_name=col,
                        original_value=None,
                        corrected_value="0" if col == FileColumns.MODEL_TOTAL_HOURS else "Unknown",
                        severity='high' if col == FileColumns.MODEL_TOTAL_HOURS else 'medium',
                        description=f"Required field '{col}' is missing or null in model data",
                        suggested_action=f"Verify model data source provides valid {col} values for all records"
                    )
                    data_quality_exceptions.append(exception)
                
                # Fill null values to allow processing to continue
                if col == FileColumns.MODEL_TOTAL_HOURS:
                    df.loc[null_mask, col] = 0.0
                elif col in [FileColumns.MODEL_LOCATION_NAME, FileColumns.MODEL_STAFF_ROLE_NAME]:
                    df.loc[null_mask, col] = 'Unknown'
        
        # Handle negative hours
        negative_hours = df[FileColumns.MODEL_TOTAL_HOURS] < 0
        if negative_hours.any():
            negative_count = negative_hours.sum()
            logger.warning(f"Found {negative_count} rows with negative model hours - capturing as data quality exceptions")
            
            # Create exceptions for negative hours
            for idx in df[negative_hours].index:
                row = df.loc[idx]
                original_val = df.loc[idx, FileColumns.MODEL_TOTAL_HOURS]
                exception = DataQualityException(
                    row_index=idx,
                    facility=row.get(FileColumns.MODEL_LOCATION_NAME, None),
                    role=row.get(FileColumns.MODEL_STAFF_ROLE_NAME, None),
                    employee_id=None,
                    issue_type='negative_hours',
                    field_name=FileColumns.MODEL_TOTAL_HOURS,
                    original_value=str(original_val),
                    corrected_value="0.0",
                    severity='medium',
                    description=f"Negative model hours value {original_val} found, corrected to 0",
                    suggested_action="Review model data source for negative hour entries and correct at source"
                )
                data_quality_exceptions.append(exception)
            
            # Set negative values to 0
            df.loc[negative_hours, FileColumns.MODEL_TOTAL_HOURS] = 0
        
        logger.info(f"Processed {initial_rows} model records, captured {len(data_quality_exceptions)} data quality issues")
        
        # Round hours to 2 decimal places
        df[FileColumns.MODEL_TOTAL_HOURS] = df[FileColumns.MODEL_TOTAL_HOURS].round(2)
        
        # Clean string columns
        df[FileColumns.MODEL_LOCATION_NAME] = df[FileColumns.MODEL_LOCATION_NAME].astype(str).str.strip()
        df[FileColumns.MODEL_STAFF_ROLE_NAME] = df[FileColumns.MODEL_STAFF_ROLE_NAME].astype(str).str.strip()
        
        # F-1a: Display formatted table (as specified in requirements)
        display_model_table(df)
        
        logger.info(f"Successfully processed {len(df)} model data records")
        return df, data_quality_exceptions
        
    except Exception as e:
        logger.error(f"Error loading model data: {str(e)}")
        raise


def display_model_table(df: pd.DataFrame) -> None:
    """
    Display model data in formatted table (F-1a requirement).
    
    Args:
        df: DataFrame with model data to display
    """
    print("\n" + "="*80)
    print("MODEL DATA LOADED (F-1a)")
    print("="*80)
    
    if df.empty:
        print("No model data loaded.")
        return
    
    # Summary statistics
    total_facilities = df[FileColumns.MODEL_LOCATION_NAME].nunique()
    total_roles = df[FileColumns.MODEL_STAFF_ROLE_NAME].nunique() 
    total_model_hours = df[FileColumns.MODEL_TOTAL_HOURS].sum()
    total_days = df[FileColumns.MODEL_DAY_OF_WEEK].nunique() if FileColumns.MODEL_DAY_OF_WEEK in df.columns else 'Unknown'
    
    print(f"Total Facilities: {total_facilities}")
    print(f"Total Roles: {total_roles}")
    print(f"Days of Week Modeled: {total_days}")
    print(f"Total Model Hours: {total_model_hours:,.2f}")
    print(f"Total Records: {len(df)} (roles × days)")
    
    # Show day-specific breakdown to highlight the daily variation
    if FileColumns.MODEL_DAY_OF_WEEK in df.columns and total_days > 1:
        print(f"\nDaily Model Hours by Day:")
        daily_hours = df.groupby(FileColumns.MODEL_DAY_OF_WEEK)[FileColumns.MODEL_TOTAL_HOURS].sum().round(2)
        for day, hours in daily_hours.items():
            print(f"  {day}: {hours:,.2f} hours")
    
    # Display sample of data in formatted table
    print("\nSample Model Data (showing day-specific hour allocations):")
    print("-" * 90)
    
    # Define column widths for display
    col_widths = {
        FileColumns.MODEL_LOCATION_NAME: 20,
        FileColumns.MODEL_STAFF_ROLE_NAME: 25,
        FileColumns.MODEL_DAY_OF_WEEK: 12,
        FileColumns.MODEL_TOTAL_HOURS: 12,
        FileColumns.MODEL_HOURS_DATE: 12
    }
    
    # Header - prioritize DayOfWeek over Date since it's more meaningful
    header_cols = [FileColumns.MODEL_LOCATION_NAME, FileColumns.MODEL_STAFF_ROLE_NAME, FileColumns.MODEL_DAY_OF_WEEK, FileColumns.MODEL_TOTAL_HOURS]
    if FileColumns.MODEL_HOURS_DATE in df.columns:
        header_cols.append(FileColumns.MODEL_HOURS_DATE)
    
    header_fmt = ''.join([f'{{:<{col_widths.get(col, 15)}}}' for col in header_cols])
    print(header_fmt.format(*header_cols))
    print("-" * 90)
    
    # Display a representative sample across different days (not just first 10)
    # Show examples from Sunday and Monday to demonstrate the day-specific model
    sunday_data = df[df[FileColumns.MODEL_DAY_OF_WEEK] == 'Sunday'].head(5)
    monday_data = df[df[FileColumns.MODEL_DAY_OF_WEEK] == 'Monday'].head(5)
    
    display_df = pd.concat([sunday_data, monday_data]).head(10)
    
    for _, row in display_df.iterrows():
        row_data = [
            str(row[FileColumns.MODEL_LOCATION_NAME])[:col_widths[FileColumns.MODEL_LOCATION_NAME]-1],
            str(row[FileColumns.MODEL_STAFF_ROLE_NAME])[:col_widths[FileColumns.MODEL_STAFF_ROLE_NAME]-1],
            str(row[FileColumns.MODEL_DAY_OF_WEEK])[:col_widths[FileColumns.MODEL_DAY_OF_WEEK]-1],
            f"{row[FileColumns.MODEL_TOTAL_HOURS]:.2f}"
        ]
        
        if FileColumns.MODEL_HOURS_DATE in df.columns and pd.notna(row[FileColumns.MODEL_HOURS_DATE]):
            # Date is kept as string for model data since we don't parse it
            row_data.append(str(row[FileColumns.MODEL_HOURS_DATE]))
        elif FileColumns.MODEL_HOURS_DATE in header_cols:
            row_data.append('N/A')
            
        print(header_fmt.format(*row_data))
    
    if len(df) > 10:
        print(f"... and {len(df) - 10} more records")
    
    print("="*90 + "\n")


def get_model_hours_summary(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Get summary statistics for model hours data.
    
    Args:
        df: DataFrame with model data
        
    Returns:
        Dictionary with summary statistics
    """
    if df.empty:
        return {
            'total_facilities': 0,
            'total_roles': 0,
            'total_model_hours': 0.0,
            'average_hours_per_role': 0.0,
            'records_count': 0
        }
    
    return {
        'total_facilities': df[FileColumns.MODEL_LOCATION_NAME].nunique(),
        'total_roles': df[FileColumns.MODEL_STAFF_ROLE_NAME].nunique(),
        'total_model_hours': float(df[FileColumns.MODEL_TOTAL_HOURS].sum()),
        'average_hours_per_role': float(df[FileColumns.MODEL_TOTAL_HOURS].mean()),
        'records_count': len(df),
        'facilities': sorted(df[FileColumns.MODEL_LOCATION_NAME].unique().tolist()),
        'roles': sorted(df[FileColumns.MODEL_STAFF_ROLE_NAME].unique().tolist())
    }


def validate_model_data(df: pd.DataFrame) -> List[str]:
    """
    Validate model data for completeness and consistency.
    
    Args:
        df: DataFrame with model data to validate
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    if df.empty:
        errors.append("Model data is empty")
        return errors
    
    # Check for required columns
    required_cols = [FileColumns.MODEL_LOCATION_NAME, FileColumns.MODEL_STAFF_ROLE_NAME, FileColumns.MODEL_TOTAL_HOURS]
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
    if FileColumns.MODEL_TOTAL_HOURS in df.columns:
        negative_hours = (df[FileColumns.MODEL_TOTAL_HOURS] < 0).sum()
        if negative_hours > 0:
            errors.append(f"Found {negative_hours} records with negative model hours")
    
    # Check for duplicate facility/role combinations
    if all(col in df.columns for col in [FileColumns.MODEL_LOCATION_NAME, FileColumns.MODEL_STAFF_ROLE_NAME]):
        duplicates = df.duplicated(subset=[FileColumns.MODEL_LOCATION_NAME, FileColumns.MODEL_STAFF_ROLE_NAME]).sum()
        if duplicates > 0:
            errors.append(f"Found {duplicates} duplicate facility/role combinations")
    
    return errors


def get_model_hours_for_facility_role(df: pd.DataFrame, facility: str, role: str) -> float:
    """
    Get model hours for a specific facility and role combination.
    Note: This function aggregates across all days of the week.
    For day-specific model hours, use get_model_hours_for_facility_role_day.
    
    Args:
        df: DataFrame with model data
        facility: Facility name
        role: Role name
        
    Returns:
        Model hours for the facility/role combination, or 0.0 if not found
    """
    match = df[(df[FileColumns.MODEL_LOCATION_NAME] == facility) & (df[FileColumns.MODEL_STAFF_ROLE_NAME] == role)]
    
    if not match.empty:
        return float(match.iloc[0][FileColumns.MODEL_TOTAL_HOURS])
    
    logger.warning(f"No model hours found for {facility} - {role}")
    return 0.0


def get_model_hours_for_facility_role_day(df: pd.DataFrame, facility: str, role: str, day_of_week: str) -> float:
    """
    Get model hours for a specific facility, role, and day of week combination.
    LEGACY FUNCTION: Uses TOTAL_HOURS for backward compatibility.
    For new model data format, use ModelDataService instead.
    
    Args:
        df: DataFrame with model data
        facility: Facility name
        role: Role name
        day_of_week: Day of the week (e.g., 'Monday', 'Sunday')
        
    Returns:
        Model hours for the facility/role/day combination, or 0.0 if not found
    """
    match = df[(df[FileColumns.MODEL_LOCATION_NAME] == facility) & (df[FileColumns.MODEL_STAFF_ROLE_NAME] == role) & (df[FileColumns.MODEL_DAY_OF_WEEK] == day_of_week)]
    
    if not match.empty:
        return float(match.iloc[0][FileColumns.MODEL_TOTAL_HOURS])
    
    logger.debug(f"No model hours found for {facility} - {role} - {day_of_week}")
    return 0.0


def get_facility_model_hours_new_format(df: pd.DataFrame, facility: str, role: str, day_of_week: str, 
                                       comparison_type: ComparisonType = ComparisonType.TOTAL_STAFF) -> float:
    """
    Get model hours for a specific facility, role, and day using the new model data format.
    Supports both total-staff and per-person comparisons.
    
    Args:
        df: DataFrame with model data (new format)
        facility: Facility name
        role: Role name
        day_of_week: Day of the week (e.g., 'Monday', 'Sunday')
        comparison_type: Type of comparison (TOTAL_STAFF or PER_PERSON)
        
    Returns:
        Expected hours based on comparison type, or 0.0 if not found
    """
    # Check if new format columns are available
    required_new_cols = [FileColumns.MODEL_DAILY_HOURS_PER_ROLE, FileColumns.MODEL_STAFF_COUNT]
    if not all(col in df.columns for col in required_new_cols):
        logger.warning("New format columns not found, falling back to legacy function")
        return get_model_hours_for_facility_role_day(df, facility, role, day_of_week)
    
    match = df[
        (df[FileColumns.MODEL_LOCATION_NAME] == facility) & 
        (df[FileColumns.MODEL_STAFF_ROLE_NAME] == role) & 
        (df[FileColumns.MODEL_DAY_OF_WEEK] == day_of_week)
    ]
    
    if match.empty:
        logger.debug(f"No model data found for {facility} - {role} - {day_of_week}")
        return 0.0
    
    record = match.iloc[0]
    daily_hours_per_role = float(record[FileColumns.MODEL_DAILY_HOURS_PER_ROLE])
    staff_count = float(record[FileColumns.MODEL_STAFF_COUNT])
    
    if comparison_type == ComparisonType.TOTAL_STAFF:
        return daily_hours_per_role * staff_count
    elif comparison_type == ComparisonType.PER_PERSON:
        return daily_hours_per_role
    else:
        raise ValueError(f"Unknown comparison type: {comparison_type}")


def get_facility_daily_hours_per_role(df: pd.DataFrame, facility: str, role: str) -> float:
    """
    Get daily hours per role for a facility/role combination from new model format.
    
    Args:
        df: DataFrame with model data (new format)
        facility: Facility name
        role: Role name
        
    Returns:
        Daily hours per role, or 0.0 if not found
    """
    if FileColumns.MODEL_DAILY_HOURS_PER_ROLE not in df.columns:
        logger.warning("DAILY_HOURS_PER_ROLE column not found in model data")
        return 0.0
    
    facility_data = df[df[FileColumns.MODEL_LOCATION_NAME] == facility]
    role_data = facility_data[facility_data[FileColumns.MODEL_STAFF_ROLE_NAME] == role]
    
    if role_data.empty:
        logger.debug(f"No model data found for {facility} - {role}")
        return 0.0
    
    # Return the daily hours per role (should be consistent across days for same role)
    return float(role_data.iloc[0][FileColumns.MODEL_DAILY_HOURS_PER_ROLE])


def get_facility_staff_count(df: pd.DataFrame, facility: str, role: str) -> float:
    """
    Get staff count for a facility/role combination from new model format.
    
    Args:
        df: DataFrame with model data (new format)
        facility: Facility name
        role: Role name
        
    Returns:
        Staff count for the role, or 0.0 if not found
    """
    if FileColumns.MODEL_STAFF_COUNT not in df.columns:
        logger.warning("STAFF_COUNT column not found in model data")
        return 0.0
    
    facility_data = df[df[FileColumns.MODEL_LOCATION_NAME] == facility]
    role_data = facility_data[facility_data[FileColumns.MODEL_STAFF_ROLE_NAME] == role]
    
    if role_data.empty:
        logger.debug(f"No model data found for {facility} - {role}")
        return 0.0
    
    # Return the staff count (should be consistent across days for same role)
    return float(role_data.iloc[0][FileColumns.MODEL_STAFF_COUNT])


def get_facility_roles(df: pd.DataFrame, facility: str) -> List[str]:
    """
    Get list of all roles for a specific facility.
    
    Args:
        df: DataFrame with model data
        facility: Facility name
        
    Returns:
        List of role names for the facility
    """
    facility_data = df[df[FileColumns.MODEL_LOCATION_NAME] == facility]
    
    if facility_data.empty:
        logger.debug(f"No model data found for facility: {facility}")
        return []
    
    roles = facility_data[FileColumns.MODEL_STAFF_ROLE_NAME].unique().tolist()
    return sorted(roles)