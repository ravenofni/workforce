"""
Unit tests for ModelDataService.

Tests cover:
- Format detection (legacy vs new)
- Facility-specific data filtering
- Dual comparison types (total-staff vs per-person)
- Backward compatibility
- Data validation and error handling
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.services.model_data_service import ModelDataService
from config.constants import FileColumns, ComparisonType


class TestModelDataService:
    """Test cases for ModelDataService."""
    
    def create_legacy_model_data(self):
        """Create sample legacy format model data (single facility)."""
        return pd.DataFrame({
            FileColumns.MODEL_LOCATION_NAME: ['Ansley Park'] * 14,
            FileColumns.MODEL_STAFF_ROLE_NAME: ['CNA', 'CNA', 'LPN', 'LPN', 'RN', 'RN', 'CMA'] * 2,
            FileColumns.MODEL_DAY_OF_WEEK: ['Monday', 'Tuesday', 'Monday', 'Tuesday', 'Monday', 'Tuesday', 'Monday'] * 2,
            FileColumns.MODEL_TOTAL_HOURS: [8.0, 8.0, 8.0, 8.0, 8.0, 8.0, 8.0, 8.0, 8.0, 8.0, 8.0, 8.0, 8.0, 8.0]
        })
    
    def create_new_model_data(self):
        """Create sample new format model data (multi-facility)."""
        data = []
        facilities = ['Facility A', 'Facility B']
        roles = [
            ('CNA', 7.5, 15),      # 15 CNAs working 7.5 hours each
            ('LPN', 8.0, 5),       # 5 LPNs working 8 hours each  
            ('RN', 8.0, 3),        # 3 RNs working 8 hours each
            ('Unmapped', 0.0, 0)   # Unmapped role with 0 staff
        ]
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        for facility in facilities:
            for role_name, daily_hours, staff_count in roles:
                for day in days:
                    data.append({
                        FileColumns.MODEL_LOCATION_KEY: f'KEY_{facility.replace(" ", "_")}',
                        FileColumns.MODEL_LOCATION_NAME: facility,
                        FileColumns.MODEL_STAFF_ROLE_NAME: role_name,
                        FileColumns.MODEL_DAY_OF_WEEK: day,
                        FileColumns.MODEL_DAILY_HOURS_PER_ROLE: daily_hours,
                        FileColumns.MODEL_STAFF_COUNT: staff_count,
                        FileColumns.MODEL_TOTAL_HOURS: daily_hours * staff_count  # Calculated field
                    })
        
        return pd.DataFrame(data)
    
    def test_format_detection_legacy(self):
        """Test detection of legacy model data format."""
        legacy_data = self.create_legacy_model_data()
        service = ModelDataService(legacy_data)
        
        assert not service._is_new_format
        
        validation = service.validate_model_data_format()
        assert validation['format_type'] == 'LEGACY'
        assert validation['facilities_count'] == 1
        assert validation['roles_count'] == 4  # CNA, LPN, RN, CMA
    
    def test_format_detection_new(self):
        """Test detection of new model data format."""
        new_data = self.create_new_model_data()
        service = ModelDataService(new_data)
        
        assert service._is_new_format
        
        validation = service.validate_model_data_format()
        assert validation['format_type'] == 'NEW'
        assert validation['facilities_count'] == 2
        assert validation['roles_count'] == 4  # CNA, LPN, RN, Unmapped
        assert validation['days_count'] == 7
    
    def test_get_all_facilities(self):
        """Test getting list of all facilities."""
        new_data = self.create_new_model_data()
        service = ModelDataService(new_data)
        
        facilities = service.get_all_facilities()
        assert facilities == ['Facility A', 'Facility B']
    
    def test_get_facility_model_data(self):
        """Test filtering model data by facility."""
        new_data = self.create_new_model_data()
        service = ModelDataService(new_data)
        
        # Test filtering for specific facility
        facility_a_data = service.get_facility_model_data('Facility A')
        assert len(facility_a_data) == 28  # 4 roles × 7 days
        assert (facility_a_data[FileColumns.MODEL_LOCATION_NAME] == 'Facility A').all()
        
        # Test non-existent facility
        empty_data = service.get_facility_model_data('Non-existent')
        assert empty_data.empty
    
    def test_get_facility_model_hours_new_format(self):
        """Test getting model hours for specific facility/role/day in new format."""
        new_data = self.create_new_model_data()
        service = ModelDataService(new_data)
        
        # Test CNA data (15 staff × 7.5 hours = 112.5 total)
        cna_info = service.get_facility_model_hours('Facility A', 'CNA', 'Monday')
        
        assert cna_info['found'] is True
        assert cna_info['daily_hours_per_role'] == 7.5
        assert cna_info['staff_count'] == 15
        assert cna_info['total_expected_hours'] == 112.5
        
        # Test unmapped role (0 staff × 0 hours = 0 total)
        unmapped_info = service.get_facility_model_hours('Facility A', 'Unmapped', 'Monday')
        
        assert unmapped_info['found'] is True
        assert unmapped_info['daily_hours_per_role'] == 0.0
        assert unmapped_info['staff_count'] == 0.0
        assert unmapped_info['total_expected_hours'] == 0.0
        
        # Test non-existent combination
        missing_info = service.get_facility_model_hours('Facility A', 'NonexistentRole', 'Monday')
        assert missing_info['found'] is False
    
    def test_get_facility_model_hours_legacy_format(self):
        """Test getting model hours for legacy format."""
        legacy_data = self.create_legacy_model_data()
        service = ModelDataService(legacy_data)
        
        # Test getting data (legacy format assumes total_hours is the expected value)
        cna_info = service.get_facility_model_hours('Ansley Park', 'CNA', 'Monday')
        
        assert cna_info['found'] is True
        assert cna_info['total_expected_hours'] == 8.0
        assert cna_info['daily_hours_per_role'] == 8.0  # Legacy assumption
        assert cna_info['staff_count'] == 1.0  # Legacy assumption
    
    def test_calculate_expected_hours_total_staff(self):
        """Test calculating expected hours for total-staff comparison."""
        new_data = self.create_new_model_data()
        service = ModelDataService(new_data)
        
        # CNA: 15 staff × 7.5 hours = 112.5 total hours
        total_expected = service.calculate_expected_hours(
            'Facility A', 'CNA', 'Monday', ComparisonType.TOTAL_STAFF
        )
        assert total_expected == 112.5
        
        # Unmapped: 0 staff × 0 hours = 0 total hours
        unmapped_expected = service.calculate_expected_hours(
            'Facility A', 'Unmapped', 'Monday', ComparisonType.TOTAL_STAFF
        )
        assert unmapped_expected == 0.0
    
    def test_calculate_expected_hours_per_person(self):
        """Test calculating expected hours for per-person comparison."""
        new_data = self.create_new_model_data()
        service = ModelDataService(new_data)
        
        # CNA: 7.5 hours per person
        per_person_expected = service.calculate_expected_hours(
            'Facility A', 'CNA', 'Monday', ComparisonType.PER_PERSON
        )
        assert per_person_expected == 7.5
        
        # LPN: 8.0 hours per person
        lpn_per_person = service.calculate_expected_hours(
            'Facility A', 'LPN', 'Monday', ComparisonType.PER_PERSON
        )
        assert lpn_per_person == 8.0
    
    def test_get_facility_role_standards(self):
        """Test getting role standards for a facility."""
        new_data = self.create_new_model_data()
        service = ModelDataService(new_data)
        
        standards = service.get_facility_role_standards('Facility A')
        
        assert len(standards) == 4  # CNA, LPN, RN, Unmapped
        
        # Check CNA standards
        cna_standards = standards['CNA']
        assert cna_standards['daily_hours_per_role'] == 7.5
        assert cna_standards['staff_count'] == 15
        assert cna_standards['days_per_week'] == 7
        
        # Check unmapped standards
        unmapped_standards = standards['Unmapped']
        assert unmapped_standards['daily_hours_per_role'] == 0.0
        assert unmapped_standards['staff_count'] == 0.0
        assert unmapped_standards['days_per_week'] == 7
    
    def test_calculate_period_model_hours_total_staff(self):
        """Test calculating model hours for a time period (total-staff)."""
        new_data = self.create_new_model_data()
        service = ModelDataService(new_data)
        
        # Calculate for one week (7 days)
        start_date = datetime(2025, 5, 5)  # Monday
        end_date = datetime(2025, 5, 11)   # Sunday
        
        period_hours = service.calculate_period_model_hours(
            'Facility A', start_date, end_date, ComparisonType.TOTAL_STAFF
        )
        
        # Expected calculation:
        # CNA: 15 × 7.5 × 7 days = 787.5 hours
        # LPN: 5 × 8.0 × 7 days = 280.0 hours  
        # RN: 3 × 8.0 × 7 days = 168.0 hours
        # Unmapped: 0 × 0.0 × 7 days = 0.0 hours
        # Total: 1,235.5 hours
        
        expected_total = (15 * 7.5 + 5 * 8.0 + 3 * 8.0 + 0 * 0.0) * 7
        assert period_hours == expected_total
        assert period_hours == 1235.5
    
    def test_calculate_period_model_hours_per_person(self):
        """Test calculating model hours for a time period (per-person)."""
        new_data = self.create_new_model_data()
        service = ModelDataService(new_data)
        
        start_date = datetime(2025, 5, 5)  # Monday  
        end_date = datetime(2025, 5, 11)   # Sunday
        
        period_hours = service.calculate_period_model_hours(
            'Facility A', start_date, end_date, ComparisonType.PER_PERSON
        )
        
        # Expected calculation (per-person hours summed across roles and days):
        # CNA: 7.5 × 7 days = 52.5 hours
        # LPN: 8.0 × 7 days = 56.0 hours
        # RN: 8.0 × 7 days = 56.0 hours  
        # Unmapped: 0.0 × 7 days = 0.0 hours
        # Total: 164.5 hours
        
        expected_total = (7.5 + 8.0 + 8.0 + 0.0) * 7
        assert period_hours == expected_total
        assert period_hours == 164.5
    
    def test_empty_data_handling(self):
        """Test service behavior with empty data."""
        empty_data = pd.DataFrame()
        service = ModelDataService(empty_data)
        
        # Should handle empty data gracefully
        assert service.get_all_facilities() == []
        
        model_info = service.get_facility_model_hours('Any Facility', 'Any Role', 'Monday')
        assert model_info['found'] is False
        assert model_info['total_expected_hours'] == 0.0
        
        period_hours = service.calculate_period_model_hours(
            'Any Facility', datetime.now(), datetime.now()
        )
        assert period_hours == 0.0
    
    def test_data_validation(self):
        """Test model data validation functionality."""
        new_data = self.create_new_model_data()
        service = ModelDataService(new_data)
        
        validation = service.validate_model_data_format()
        
        assert validation['format_type'] == 'NEW'
        assert validation['total_records'] == 56  # 2 facilities × 4 roles × 7 days
        assert validation['facilities_count'] == 2
        assert validation['roles_count'] == 4
        assert validation['days_count'] == 7
        assert len(validation['validation_errors']) == 0
        assert len(validation['warnings']) == 0
    
    def test_data_validation_with_missing_columns(self):
        """Test validation with missing required columns."""
        # Create data missing required columns
        incomplete_data = pd.DataFrame({
            FileColumns.MODEL_LOCATION_NAME: ['Facility A'],
            # Missing STAFF_ROLE_NAME and other required columns
        })
        
        service = ModelDataService(incomplete_data)
        validation = service.validate_model_data_format()
        
        assert len(validation['validation_errors']) > 0
        assert any('Missing required columns' in error for error in validation['validation_errors'])
    
    def test_get_model_summary(self):
        """Test getting model data summary."""
        new_data = self.create_new_model_data()
        service = ModelDataService(new_data)
        
        summary = service.get_model_summary()
        
        assert summary['format_type'] == 'NEW'
        assert summary['total_records'] == 56
        assert summary['facilities'] == ['Facility A', 'Facility B']
        
        # Check roles by facility
        assert 'Facility A' in summary['roles_by_facility']
        assert 'CNA' in summary['roles_by_facility']['Facility A']
        assert 'Unmapped' in summary['roles_by_facility']['Facility A']
        
        # Check coverage (should be 7 days for each role)
        assert summary['coverage']['Facility A']['CNA'] == 7
        assert summary['coverage']['Facility A']['Unmapped'] == 7
        
        # Check total model hours calculation
        # Each facility: (15*7.5 + 5*8.0 + 3*8.0 + 0*0.0) * 7 days = 1,235.5 hours
        # Two facilities: 1,235.5 * 2 = 2,471.0 hours
        expected_total = 2 * (15 * 7.5 + 5 * 8.0 + 3 * 8.0 + 0 * 0.0) * 7
        assert summary['total_model_hours'] == expected_total
    
    def test_comparison_type_validation(self):
        """Test validation of comparison type parameter."""
        new_data = self.create_new_model_data()
        service = ModelDataService(new_data)
        
        # Test invalid comparison type
        with pytest.raises(ValueError, match="Unknown comparison type"):
            service.calculate_expected_hours(
                'Facility A', 'CNA', 'Monday', 'invalid_type'
            )
    
    def test_backward_compatibility(self):
        """Test that service works with both legacy and new formats."""
        # Test legacy format
        legacy_data = self.create_legacy_model_data()
        legacy_service = ModelDataService(legacy_data)
        
        legacy_info = legacy_service.get_facility_model_hours('Ansley Park', 'CNA', 'Monday')
        assert legacy_info['found'] is True
        assert legacy_info['total_expected_hours'] == 8.0
        
        # Test new format
        new_data = self.create_new_model_data()
        new_service = ModelDataService(new_data)
        
        new_info = new_service.get_facility_model_hours('Facility A', 'CNA', 'Monday')
        assert new_info['found'] is True
        assert new_info['total_expected_hours'] == 112.5
        
        # Both should work without errors
        assert legacy_service.get_all_facilities() == ['Ansley Park']
        assert new_service.get_all_facilities() == ['Facility A', 'Facility B']