"""
Data normalization (F-2) - Standardize date/time, convert hours, harmonize role names.
Implements F-2 requirements for data standardization.
"""

import pandas as pd
import re
from typing import Dict, List, Optional
import logging
from datetime import datetime

from config.constants import DATE_FORMAT, FileColumns
from src.models.data_models import DataQualityException


logger = logging.getLogger(__name__)


def standardize_datetime(df: pd.DataFrame, date_column: str = 'Date', 
                         facility_col: Optional[str] = None, role_col: Optional[str] = None, 
                         employee_col: Optional[str] = None) -> tuple[pd.DataFrame, List[DataQualityException]]:
    """
    Standardize date/time using MMDDYYYY as the preferred format (F-2).
    
    Args:
        df: DataFrame containing date column to standardize
        date_column: Name of the date column to standardize
        facility_col: Column name for facility information (for exception tracking)
        role_col: Column name for role information (for exception tracking)
        employee_col: Column name for employee information (for exception tracking)
        
    Returns:
        Tuple of (DataFrame with standardized date column, List of data quality exceptions)
        
    Raises:
        ValueError: If date column is missing or cannot be parsed
    """
    if date_column not in df.columns:
        raise ValueError(f"Date column '{date_column}' not found in DataFrame")
    
    df = df.copy()
    original_count = len(df)
    data_quality_exceptions = []
    
    logger.info(f"Standardizing {date_column} column using format {DATE_FORMAT}")
    
    try:
        # Store original values for exception tracking
        original_dates = df[date_column].copy()
        
        # CRITICAL: Use explicit format strings for MMDDYYYY format
        df[date_column] = pd.to_datetime(df[date_column], format=DATE_FORMAT, errors='coerce')
        
        # Identify failed conversions and create exceptions instead of dropping
        null_date_mask = df[date_column].isnull()
        null_dates = null_date_mask.sum()
        
        if null_dates > 0:
            logger.warning(f"Failed to parse {null_dates} dates out of {original_count} records - capturing as data quality exceptions")
            
            # Create data quality exceptions for failed date parsing
            for idx in df[null_date_mask].index:
                row = df.loc[idx]
                exception = DataQualityException(
                    row_index=idx,
                    facility=row.get(facility_col, None) if facility_col else None,
                    role=row.get(role_col, None) if role_col else None,
                    employee_id=row.get(employee_col, None) if employee_col else None,
                    issue_type='date_parsing_failed',
                    field_name=date_column,
                    original_value=str(original_dates.loc[idx]) if pd.notna(original_dates.loc[idx]) else None,
                    corrected_value=None,
                    severity='high',
                    description=f"Date value '{original_dates.loc[idx]}' could not be parsed using format {DATE_FORMAT}",
                    suggested_action="Verify date format matches expected MMDDYYYY or update date format configuration"
                )
                data_quality_exceptions.append(exception)
            
            # Set failed dates to a placeholder or NaT (but don't drop the rows)
            # Keep the original string value in a backup column for reference
            df[f'{date_column}_original'] = original_dates
        
        logger.info(f"Successfully processed {len(df)} date records ({len(data_quality_exceptions)} with quality issues)")
        return df, data_quality_exceptions
        
    except Exception as e:
        logger.error(f"Error standardizing dates: {str(e)}")
        raise ValueError(f"Unable to standardize date column: {str(e)}")


def convert_hours_to_float(df: pd.DataFrame, hours_columns: List[str],
                          facility_col: Optional[str] = None, role_col: Optional[str] = None, 
                          employee_col: Optional[str] = None) -> tuple[pd.DataFrame, List[DataQualityException]]:
    """
    Convert hours columns to float with proper validation (F-2).
    
    Args:
        df: DataFrame containing hours columns
        hours_columns: List of column names containing hours data
        facility_col: Column name for facility information (for exception tracking)
        role_col: Column name for role information (for exception tracking)
        employee_col: Column name for employee information (for exception tracking)
        
    Returns:
        Tuple of (DataFrame with hours columns converted to float, List of data quality exceptions)
        
    Raises:
        ValueError: If hours columns are missing or contain invalid data
    """
    df = df.copy()
    data_quality_exceptions = []
    
    for col in hours_columns:
        if col not in df.columns:
            logger.warning(f"Hours column '{col}' not found in DataFrame")
            continue
        
        logger.info(f"Converting {col} to float")
        
        # Store original values for exception tracking
        original_values = df[col].copy()
        original_count = len(df)
        
        # Convert to numeric, handling various formats
        df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Identify conversion failures and create exceptions
        null_hours_mask = df[col].isnull()
        null_hours = null_hours_mask.sum()
        if null_hours > 0:
            logger.warning(f"Failed to convert {null_hours} values in {col} column - capturing as data quality exceptions")
            
            # Create exceptions for failed conversions
            for idx in df[null_hours_mask].index:
                row = df.loc[idx]
                exception = DataQualityException(
                    row_index=idx,
                    facility=row.get(facility_col, None) if facility_col else None,
                    role=row.get(role_col, None) if role_col else None,
                    employee_id=row.get(employee_col, None) if employee_col else None,
                    issue_type='hours_conversion_failed',
                    field_name=col,
                    original_value=str(original_values.loc[idx]) if pd.notna(original_values.loc[idx]) else None,
                    corrected_value="0.0",
                    severity='medium',
                    description=f"Hours value '{original_values.loc[idx]}' could not be converted to numeric format",
                    suggested_action="Verify hours data contains valid numeric values"
                )
                data_quality_exceptions.append(exception)
            
            # Set failed conversions to 0 for processing continuity
            df.loc[null_hours_mask, col] = 0.0
        
        # Identify and handle negative values
        negative_mask = (df[col] < 0)
        negative_count = negative_mask.sum()
        if negative_count > 0:
            logger.warning(f"Found {negative_count} negative values in {col} - capturing as data quality exceptions")
            
            # Create exceptions for negative hours
            for idx in df[negative_mask].index:
                row = df.loc[idx]
                original_val = df.loc[idx, col]
                exception = DataQualityException(
                    row_index=idx,
                    facility=row.get(facility_col, None) if facility_col else None,
                    role=row.get(role_col, None) if role_col else None,
                    employee_id=row.get(employee_col, None) if employee_col else None,
                    issue_type='negative_hours',
                    field_name=col,
                    original_value=str(original_val),
                    corrected_value="0.0",
                    severity='medium',
                    description=f"Negative hours value {original_val} found, corrected to 0",
                    suggested_action="Review data source for negative hour entries and correct at source"
                )
                data_quality_exceptions.append(exception)
            
            # Set negative values to 0
            df.loc[negative_mask, col] = 0.0
        
        # Round to 2 decimal places for consistency
        df[col] = df[col].round(2)
        
        logger.info(f"Successfully processed {col}: {original_count} records ({len([e for e in data_quality_exceptions if e.field_name == col])} with quality issues)")
    
    return df, data_quality_exceptions


def harmonize_role_names(df: pd.DataFrame, role_column: str = 'Role') -> pd.DataFrame:
    """
    Harmonize role names for case and spelling consistency (F-2).
    
    Args:
        df: DataFrame containing role column to harmonize
        role_column: Name of the role column to harmonize
        
    Returns:
        DataFrame with harmonized role names
    """
    if role_column not in df.columns:
        logger.warning(f"Role column '{role_column}' not found in DataFrame")
        return df
    
    df = df.copy()
    original_unique_roles = df[role_column].nunique()
    
    logger.info(f"Harmonizing {role_column} column - {original_unique_roles} unique roles found")
    
    # Apply harmonization rules
    df[role_column] = df[role_column].apply(_harmonize_single_role)
    
    new_unique_roles = df[role_column].nunique()
    logger.info(f"Role harmonization complete: {new_unique_roles} unique roles after harmonization")
    
    if new_unique_roles < original_unique_roles:
        logger.info(f"Consolidated {original_unique_roles - new_unique_roles} duplicate role variations")
    
    return df


def _harmonize_single_role(role_name: str) -> str:
    """
    Apply harmonization rules to a single role name.
    
    Args:
        role_name: Original role name
        
    Returns:
        Harmonized role name
    """
    if pd.isna(role_name) or not isinstance(role_name, str):
        return str(role_name)
    
    # Basic cleaning
    harmonized = role_name.strip()
    
    # Standardize common abbreviations and variations
    harmonization_rules = {
        # Nursing roles
        r'\bRN\b': 'RN',
        r'\bLPN\b': 'LPN',
        r'\bCNA\b': 'CNA',
        r'\bADON\b': 'ADON',
        r'\bDON\b': 'DON',
        
        # Common abbreviations
        r'\bSuprv\.?\b': 'Supervisor',
        r'\bSupervisor\b': 'Supervisor',
        r'\bHskpg\.?\b': 'Housekeeping',
        r'\bHousekeeping\b': 'Housekeeping',
        r'\bMed\.?\b': 'Medication',
        r'\bCert\.?\b': 'Certified',
        r'\bAsst\.?\b': 'Assistant',
        r'\bWknd\.?\b': 'Weekend',
        
        # Standardize spacing and punctuation
        r'\s+': ' ',  # Multiple spaces to single space
        r'\.+': '.',  # Multiple periods to single period
    }
    
    # Apply rules
    for pattern, replacement in harmonization_rules.items():
        harmonized = re.sub(pattern, replacement, harmonized, flags=re.IGNORECASE)
    
    # Title case for consistency
    harmonized = harmonized.title()
    
    # Final cleanup
    harmonized = harmonized.strip()
    
    return harmonized


def normalize_facility_names(df: pd.DataFrame, facility_column: str = 'Facility') -> pd.DataFrame:
    """
    Normalize facility names for consistency.
    
    Args:
        df: DataFrame containing facility column to normalize
        facility_column: Name of the facility column to normalize
        
    Returns:
        DataFrame with normalized facility names
    """
    if facility_column not in df.columns:
        logger.warning(f"Facility column '{facility_column}' not found in DataFrame")
        return df
    
    df = df.copy()
    original_unique_facilities = df[facility_column].nunique()
    
    logger.info(f"Normalizing {facility_column} column - {original_unique_facilities} unique facilities found")
    
    # Basic normalization
    df[facility_column] = df[facility_column].astype(str).str.strip()
    df[facility_column] = df[facility_column].str.title()
    
    new_unique_facilities = df[facility_column].nunique()
    logger.info(f"Facility normalization complete: {new_unique_facilities} unique facilities after normalization")
    
    return df


def normalize_all_data(df: pd.DataFrame, date_columns: List[str] = None, 
                      hours_columns: List[str] = None, skip_date_normalization: bool = False,
                      facility_col: Optional[str] = None, role_col: Optional[str] = None, 
                      employee_col: Optional[str] = None) -> tuple[pd.DataFrame, List[DataQualityException]]:
    """
    Apply all normalization steps to the DataFrame (F-2 complete implementation).
    
    Args:
        df: DataFrame to normalize
        date_columns: List of date columns to standardize
        hours_columns: List of hours columns to convert
        skip_date_normalization: If True, skip date standardization (useful for model data)
        facility_col: Column name for facility information (for exception tracking)
        role_col: Column name for role information (for exception tracking)
        employee_col: Column name for employee information (for exception tracking)
        
    Returns:
        Tuple of (Fully normalized DataFrame, List of data quality exceptions)
    """
    if df.empty:
        logger.warning("Empty DataFrame provided for normalization")
        return df, []
    
    logger.info(f"Starting complete data normalization for {len(df)} records")
    
    df_normalized = df.copy()
    all_exceptions = []
    
    # Default column lists if not provided
    if date_columns is None:
        date_columns = []
    if hours_columns is None:
        hours_columns = []
    
    try:
        # Standardize date columns (skip if requested - useful for model data)
        if not skip_date_normalization:
            for date_col in date_columns:
                if date_col in df_normalized.columns:
                    df_normalized, date_exceptions = standardize_datetime(df_normalized, date_col, facility_col, role_col, employee_col)
                    all_exceptions.extend(date_exceptions)
        else:
            logger.info("Skipping date normalization as requested")
        
        # Convert hours columns to float
        available_hours_cols = [col for col in hours_columns if col in df_normalized.columns]
        if available_hours_cols:
            df_normalized, hours_exceptions = convert_hours_to_float(df_normalized, available_hours_cols, facility_col, role_col, employee_col)
            all_exceptions.extend(hours_exceptions)
        
        # Harmonize role names
        if role_col and role_col in df_normalized.columns:
            df_normalized = harmonize_role_names(df_normalized, role_col)
        
        # Normalize facility names
        if facility_col and facility_col in df_normalized.columns:
            df_normalized = normalize_facility_names(df_normalized, facility_col)
        
        logger.info(f"Data normalization complete: {len(df_normalized)} records processed, {len(all_exceptions)} data quality issues captured")
        
        return df_normalized, all_exceptions
        
    except Exception as e:
        logger.error(f"Error during data normalization: {str(e)}")
        raise


def validate_normalized_data(df: pd.DataFrame) -> List[str]:
    """
    Validate that data normalization was successful.
    
    Args:
        df: Normalized DataFrame to validate
        
    Returns:
        List of validation issues found
    """
    issues = []
    
    if df.empty:
        issues.append("DataFrame is empty after normalization")
        return issues
    
    # Check date columns
    date_columns = ['Date', 'WeekStart']
    for col in date_columns:
        if col in df.columns:
            if not pd.api.types.is_datetime64_any_dtype(df[col]):
                issues.append(f"Column {col} is not datetime type after normalization")
            
            null_count = df[col].isnull().sum()
            if null_count > 0:
                issues.append(f"Column {col} has {null_count} null values after normalization")
    
    # Check hours columns
    hours_columns = ['ActualHours', 'ModelHours']
    for col in hours_columns:
        if col in df.columns:
            if not pd.api.types.is_numeric_dtype(df[col]):
                issues.append(f"Column {col} is not numeric type after normalization")
            
            negative_count = (df[col] < 0).sum()
            if negative_count > 0:
                issues.append(f"Column {col} has {negative_count} negative values after normalization")
    
    # Check string columns
    string_columns = ['Facility', 'Role']
    for col in string_columns:
        if col in df.columns:
            empty_strings = (df[col].astype(str).str.strip() == '').sum()
            if empty_strings > 0:
                issues.append(f"Column {col} has {empty_strings} empty values after normalization")
    
    return issues


def get_normalization_summary(original_df: pd.DataFrame, normalized_df: pd.DataFrame) -> Dict[str, any]:
    """
    Generate summary of normalization changes.
    
    Args:
        original_df: DataFrame before normalization
        normalized_df: DataFrame after normalization
        
    Returns:
        Dictionary with normalization summary statistics
    """
    summary = {
        'original_records': len(original_df),
        'normalized_records': len(normalized_df),
        'records_removed': len(original_df) - len(normalized_df),
        'normalization_success_rate': len(normalized_df) / len(original_df) * 100 if len(original_df) > 0 else 0
    }
    
    # Compare unique values in key columns
    for col in ['Facility', 'Role']:
        if col in original_df.columns and col in normalized_df.columns:
            original_unique = original_df[col].nunique()
            normalized_unique = normalized_df[col].nunique()
            summary[f'{col.lower()}_original_unique'] = original_unique
            summary[f'{col.lower()}_normalized_unique'] = normalized_unique
            summary[f'{col.lower()}_consolidation'] = original_unique - normalized_unique
    
    return summary