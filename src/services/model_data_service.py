"""
Model Data Service Layer for Workforce Analytics.

This service provides facility-aware model data operations supporting both
single-facility legacy format and multi-facility new format with dynamic
role standards and dual comparison types (total-staff vs per-person).

Key Features:
- Facility-specific model data filtering using LOCATION_KEY
- Support for both TOTAL_HOURS (legacy) and DAILY_HOURS_PER_ROLE + STAFF_COUNT (new)
- Dual comparison framework: total-staff (budget) vs per-person (workload)
- Backward compatibility with existing single-facility model data

Example Usage:
    from src.services.model_data_service import ModelDataService
    
    service = ModelDataService(model_df)
    
    # Get facility-specific model hours
    model_info = service.get_facility_model_hours("Facility A", "CNA", "Monday")
    # Returns: {daily_hours_per_role: 7.5, staff_count: 15, total_expected_hours: 112.5}
    
    # Calculate expected hours for comparison
    expected_total = service.calculate_expected_hours("Facility A", "CNA", "Monday", ComparisonType.TOTAL_STAFF)
    expected_per_person = service.calculate_expected_hours("Facility A", "CNA", "Monday", ComparisonType.PER_PERSON)
"""

import pandas as pd
import logging
from typing import Dict, Optional, List, Any, Union
from datetime import datetime, timedelta

from config.constants import FileColumns, ComparisonType


logger = logging.getLogger(__name__)


class ModelDataService:
    """Service for facility-aware model data operations."""
    
    def __init__(self, model_data: pd.DataFrame):
        """
        Initialize the model data service.
        
        Args:
            model_data: DataFrame with model hours data (single or multi-facility)
        """
        self.model_data = model_data
        self._is_new_format = self._detect_model_format()
        
        logger.info(f"ModelDataService initialized with {len(model_data)} records")
        logger.info(f"Model format detected: {'NEW' if self._is_new_format else 'LEGACY'}")
        
        if self._is_new_format:
            facilities = self.get_all_facilities()
            logger.info(f"Multi-facility model data with {len(facilities)} facilities: {facilities}")
    
    def _detect_model_format(self) -> bool:
        """
        Detect if model data uses new format with DAILY_HOURS_PER_ROLE and STAFF_COUNT.
        
        Returns:
            True if new format, False if legacy format
        """
        required_new_cols = [FileColumns.MODEL_DAILY_HOURS_PER_ROLE, FileColumns.MODEL_STAFF_COUNT]
        has_new_cols = all(col in self.model_data.columns for col in required_new_cols)
        
        # Also check if we have facility keys (multiple facilities)
        has_facility_keys = FileColumns.MODEL_LOCATION_KEY in self.model_data.columns
        multiple_facilities = False
        if has_facility_keys:
            multiple_facilities = self.model_data[FileColumns.MODEL_LOCATION_KEY].nunique() > 1
        
        # If we have the new columns, it's new format regardless of facility count
        is_new_format = has_new_cols
        
        logger.debug(f"Format detection: new_cols={has_new_cols}, facility_keys={has_facility_keys}, "
                    f"multiple_facilities={multiple_facilities}, is_new={is_new_format}")
        
        return is_new_format
    
    def get_all_facilities(self) -> List[str]:
        """
        Get list of all facilities in the model data.
        
        Returns:
            List of facility names
        """
        if FileColumns.MODEL_LOCATION_NAME in self.model_data.columns:
            return sorted(self.model_data[FileColumns.MODEL_LOCATION_NAME].unique().tolist())
        return []
    
    def get_facility_model_data(self, facility: str) -> pd.DataFrame:
        """
        Get model data filtered for a specific facility.
        
        Args:
            facility: Facility name to filter by
            
        Returns:
            DataFrame with model data for the specified facility
        """
        if not self._is_new_format:
            # Legacy format: assume all data is for the requested facility
            return self.model_data.copy()
        
        # New format: filter by facility name
        if FileColumns.MODEL_LOCATION_NAME not in self.model_data.columns:
            logger.warning(f"Cannot filter by facility '{facility}' - no location name column")
            return pd.DataFrame()
        
        facility_data = self.model_data[
            self.model_data[FileColumns.MODEL_LOCATION_NAME] == facility
        ].copy()
        
        if facility_data.empty:
            available_facilities = self.model_data[FileColumns.MODEL_LOCATION_NAME].unique()
            logger.warning(f"No model data found for facility: '{facility}' | Available: {list(available_facilities)}")
        else:
            logger.debug(f"Retrieved {len(facility_data)} model records for facility: {facility}")
        
        return facility_data
    
    def get_facility_model_hours(self, facility: str, role: str, day_of_week: str) -> Dict[str, float]:
        """
        Get model hours information for a specific facility, role, and day.
        
        Args:
            facility: Facility name
            role: Staff role name
            day_of_week: Day of the week (e.g., 'Monday', 'Sunday')
            
        Returns:
            Dictionary with model hour information:
            {
                'daily_hours_per_role': float,    # Hours per individual staff member
                'staff_count': float,             # Number of staff for this role
                'total_expected_hours': float,    # Total hours for all staff (daily_hours * staff_count)
                'found': bool                     # Whether data was found
            }
        """
        facility_data = self.get_facility_model_data(facility)
        
        if facility_data.empty:
            return {
                'daily_hours_per_role': 0.0,
                'staff_count': 0.0,
                'total_expected_hours': 0.0,
                'found': False
            }
        
        # Filter for specific role and day
        role_day_data = facility_data[
            (facility_data[FileColumns.MODEL_STAFF_ROLE_NAME] == role) &
            (facility_data[FileColumns.MODEL_DAY_OF_WEEK] == day_of_week)
        ]
        
        if role_day_data.empty:
            logger.debug(f"No model data found for {facility} - {role} - {day_of_week}")
            return {
                'daily_hours_per_role': 0.0,
                'staff_count': 0.0,
                'total_expected_hours': 0.0,
                'found': False
            }
        
        # Get the first matching record
        record = role_day_data.iloc[0]
        
        if self._is_new_format:
            # New format: use DAILY_HOURS_PER_ROLE and STAFF_COUNT
            daily_hours = float(record[FileColumns.MODEL_DAILY_HOURS_PER_ROLE])
            staff_count = float(record[FileColumns.MODEL_STAFF_COUNT])
            total_hours = daily_hours * staff_count
        else:
            # Legacy format: TOTAL_HOURS represents aggregate, assume 1 person or derive per-person
            total_hours = float(record[FileColumns.MODEL_TOTAL_HOURS])
            # For legacy, we'll assume the total hours represent the expected total
            # and derive per-person hours if we can determine staff count from actual data
            daily_hours = total_hours  # Default assumption: total_hours is per-person
            staff_count = 1.0  # Default assumption: 1 person
        
        result = {
            'daily_hours_per_role': daily_hours,
            'staff_count': staff_count,
            'total_expected_hours': total_hours,
            'found': True
        }
        
        logger.debug(f"Model data for {facility}-{role}-{day_of_week}: {result}")
        return result
    
    def calculate_expected_hours(self, facility: str, role: str, day_of_week: str, 
                               comparison_type: ComparisonType = ComparisonType.TOTAL_STAFF) -> float:
        """
        Calculate expected hours for comparison based on comparison type.
        
        Args:
            facility: Facility name
            role: Staff role name  
            day_of_week: Day of the week
            comparison_type: Type of comparison (TOTAL_STAFF or PER_PERSON)
            
        Returns:
            Expected hours for comparison
        """
        model_info = self.get_facility_model_hours(facility, role, day_of_week)
        
        if not model_info['found']:
            return 0.0
        
        if comparison_type == ComparisonType.TOTAL_STAFF:
            return model_info['total_expected_hours']
        elif comparison_type == ComparisonType.PER_PERSON:
            return model_info['daily_hours_per_role']
        else:
            raise ValueError(f"Unknown comparison type: {comparison_type}")
    
    def get_facility_role_standards(self, facility: str) -> Dict[str, Dict[str, float]]:
        """
        Get role standards for all roles in a facility.
        
        Args:
            facility: Facility name
            
        Returns:
            Dictionary mapping role names to their standards:
            {
                'role_name': {
                    'daily_hours_per_role': float,
                    'staff_count': float,
                    'days_per_week': int
                }
            }
        """
        facility_data = self.get_facility_model_data(facility)
        
        if facility_data.empty:
            return {}
        
        role_standards = {}
        
        # Group by role to get standards
        for role in facility_data[FileColumns.MODEL_STAFF_ROLE_NAME].unique():
            role_data = facility_data[facility_data[FileColumns.MODEL_STAFF_ROLE_NAME] == role]
            
            if self._is_new_format:
                # Get first record for role (standards should be consistent across days)
                first_record = role_data.iloc[0]
                daily_hours = float(first_record[FileColumns.MODEL_DAILY_HOURS_PER_ROLE])
                staff_count = float(first_record[FileColumns.MODEL_STAFF_COUNT])
            else:
                # Legacy format: derive from available data
                daily_hours = float(role_data[FileColumns.MODEL_TOTAL_HOURS].iloc[0])
                staff_count = 1.0
            
            days_per_week = len(role_data)  # How many days this role is scheduled
            
            role_standards[role] = {
                'daily_hours_per_role': daily_hours,
                'staff_count': staff_count,
                'days_per_week': days_per_week
            }
        
        logger.debug(f"Role standards for {facility}: {len(role_standards)} roles")
        return role_standards
    
    def calculate_period_model_hours(self, facility: str, analysis_start_date: datetime, 
                                   analysis_end_date: datetime,
                                   comparison_type: ComparisonType = ComparisonType.TOTAL_STAFF) -> float:
        """
        Calculate expected model hours for a facility over a specific time period.
        Optimized version using arithmetic instead of date iteration.
        
        Args:
            facility: Facility name
            analysis_start_date: Start date of analysis period
            analysis_end_date: End date of analysis period
            comparison_type: Type of comparison (TOTAL_STAFF or PER_PERSON)
            
        Returns:
            Total expected hours for the period
        """
        facility_data = self.get_facility_model_data(facility)
        
        if facility_data.empty:
            logger.warning(f"No model data found for facility: {facility}")
            return 0.0
        
        # Calculate period days
        period_days = (analysis_end_date - analysis_start_date).days + 1
        
        if self._is_new_format:
            # New format: use DAILY_HOURS_PER_ROLE and STAFF_COUNT for efficient calculation
            # Group by role to avoid counting same role multiple times (once per day)
            role_data = facility_data.groupby(FileColumns.MODEL_STAFF_ROLE_NAME).first()
            
            if comparison_type == ComparisonType.TOTAL_STAFF:
                # Sum: (daily_hours_per_role × staff_count) for all roles × period_days
                daily_total = (
                    role_data[FileColumns.MODEL_DAILY_HOURS_PER_ROLE] * 
                    role_data[FileColumns.MODEL_STAFF_COUNT]
                ).sum()
            else:  # PER_PERSON
                # Sum: daily_hours_per_role for all roles × period_days
                daily_total = role_data[FileColumns.MODEL_DAILY_HOURS_PER_ROLE].sum()
            total_period_hours = daily_total * period_days
                
        else:
            # Legacy format: use TOTAL_HOURS directly
            # Assume model data represents daily totals, multiply by period days
            daily_total = facility_data[FileColumns.MODEL_TOTAL_HOURS].mean()  # Average daily total
            total_period_hours = daily_total * period_days
        
        logger.debug(f"Period model calculation for {facility}: {period_days} days = {total_period_hours:.2f} hours (optimized)")
        return total_period_hours
    
    def validate_model_data_format(self) -> Dict[str, Any]:
        """
        Validate the model data format and return diagnostic information.
        
        Returns:
            Dictionary with validation results and diagnostics
        """
        diagnostics = {
            'format_type': 'NEW' if self._is_new_format else 'LEGACY',
            'total_records': len(self.model_data),
            'columns_present': list(self.model_data.columns),
            'facilities_count': 0,
            'roles_count': 0,
            'days_count': 0,
            'validation_errors': [],
            'warnings': []
        }
        
        # Count unique values
        if FileColumns.MODEL_LOCATION_NAME in self.model_data.columns:
            diagnostics['facilities_count'] = self.model_data[FileColumns.MODEL_LOCATION_NAME].nunique()
            
        if FileColumns.MODEL_STAFF_ROLE_NAME in self.model_data.columns:
            diagnostics['roles_count'] = self.model_data[FileColumns.MODEL_STAFF_ROLE_NAME].nunique()
            
        if FileColumns.MODEL_DAY_OF_WEEK in self.model_data.columns:
            diagnostics['days_count'] = self.model_data[FileColumns.MODEL_DAY_OF_WEEK].nunique()
        
        # Validate required columns
        if self._is_new_format:
            required_cols = [
                FileColumns.MODEL_LOCATION_NAME,
                FileColumns.MODEL_STAFF_ROLE_NAME,
                FileColumns.MODEL_DAY_OF_WEEK,
                FileColumns.MODEL_DAILY_HOURS_PER_ROLE,
                FileColumns.MODEL_STAFF_COUNT
            ]
        else:
            required_cols = [
                FileColumns.MODEL_LOCATION_NAME,
                FileColumns.MODEL_STAFF_ROLE_NAME,
                FileColumns.MODEL_TOTAL_HOURS
            ]
        
        missing_cols = [col for col in required_cols if col not in self.model_data.columns]
        if missing_cols:
            diagnostics['validation_errors'].append(f"Missing required columns: {missing_cols}")
        
        # Check for data quality issues
        if not self.model_data.empty:
            # Check for null values in critical columns
            for col in [FileColumns.MODEL_LOCATION_NAME, FileColumns.MODEL_STAFF_ROLE_NAME]:
                if col in self.model_data.columns:
                    null_count = self.model_data[col].isnull().sum()
                    if null_count > 0:
                        diagnostics['warnings'].append(f"Found {null_count} null values in {col}")
        
        logger.info(f"Model data validation: {diagnostics['format_type']} format, "
                   f"{diagnostics['facilities_count']} facilities, "
                   f"{diagnostics['roles_count']} roles, "
                   f"{len(diagnostics['validation_errors'])} errors")
        
        return diagnostics
    
    def get_model_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the model data for reporting purposes.
        
        Returns:
            Dictionary with model data summary
        """
        summary = {
            'format_type': 'NEW' if self._is_new_format else 'LEGACY',
            'total_records': len(self.model_data),
            'facilities': [],
            'total_model_hours': 0.0,
            'roles_by_facility': {},
            'coverage': {}
        }
        
        if self.model_data.empty:
            return summary
        
        # Get facilities
        facilities = self.get_all_facilities()
        summary['facilities'] = facilities
        
        # Calculate totals and coverage
        for facility in facilities:
            facility_data = self.get_facility_model_data(facility)
            
            if self._is_new_format:
                facility_total = (
                    facility_data[FileColumns.MODEL_DAILY_HOURS_PER_ROLE] * 
                    facility_data[FileColumns.MODEL_STAFF_COUNT]
                ).sum()
            else:
                facility_total = facility_data[FileColumns.MODEL_TOTAL_HOURS].sum()
            
            summary['total_model_hours'] += facility_total
            
            # Roles per facility
            roles = facility_data[FileColumns.MODEL_STAFF_ROLE_NAME].unique().tolist()
            summary['roles_by_facility'][facility] = sorted(roles)
            
            # Coverage (days per role)
            if FileColumns.MODEL_DAY_OF_WEEK in facility_data.columns:
                role_coverage = facility_data.groupby(FileColumns.MODEL_STAFF_ROLE_NAME)[FileColumns.MODEL_DAY_OF_WEEK].nunique().to_dict()
                summary['coverage'][facility] = role_coverage
        
        return summary