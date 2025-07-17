"""
Test suite for overtime analysis functionality.

Tests the overtime analysis module including role-specific shift hours,
overtime calculation, and data model validation.
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import patch

from src.analysis.overtime_analysis import (
    calculate_daily_overtime,
    get_employee_primary_role,
    calculate_employee_overtime,
    calculate_overtime_analysis,
    validate_overtime_data,
    analyze_overtime_by_role
)
from src.models.data_models import OvertimeEmployee, OvertimeAnalysis
from config.constants import FileColumns


class TestOvertimeCalculation:
    """Test basic overtime calculation functions."""
    
    def test_calculate_daily_overtime_no_overtime(self):
        """Test overtime calculation when no overtime worked."""
        result = calculate_daily_overtime(8.0, 8.0)
        assert result == 0.0
        
        result = calculate_daily_overtime(7.5, 8.0)
        assert result == 0.0
    
    def test_calculate_daily_overtime_with_overtime(self):
        """Test overtime calculation when overtime is worked."""
        result = calculate_daily_overtime(10.0, 8.0)
        assert result == 2.0
        
        result = calculate_daily_overtime(12.5, 8.0)
        assert result == 4.5
    
    def test_calculate_daily_overtime_edge_cases(self):
        """Test overtime calculation edge cases."""
        # Exactly at threshold
        result = calculate_daily_overtime(8.0, 8.0)
        assert result == 0.0
        
        # Very small overtime
        result = calculate_daily_overtime(8.01, 8.0)
        assert result == 0.01


class TestEmployeePrimaryRole:
    """Test employee primary role determination."""
    
    def test_get_employee_primary_role_single_role(self):
        """Test primary role when employee has only one role."""
        df = pd.DataFrame({
            FileColumns.FACILITY_STAFF_ROLE_NAME: ['Charge Nurse (LPN)'],
            FileColumns.FACILITY_TOTAL_HOURS: [8.0]
        })
        
        result = get_employee_primary_role(df)
        assert result == 'Charge Nurse (LPN)'
    
    def test_get_employee_primary_role_multiple_roles(self):
        """Test primary role when employee has multiple roles."""
        df = pd.DataFrame({
            FileColumns.FACILITY_STAFF_ROLE_NAME: ['Charge Nurse (LPN)', 'Certified Nursing Assistant', 'Charge Nurse (LPN)'],
            FileColumns.FACILITY_TOTAL_HOURS: [8.0, 4.0, 7.0]
        })
        
        result = get_employee_primary_role(df)
        assert result == 'Charge Nurse (LPN)'  # 15 total hours vs 4 for CNA
    
    def test_get_employee_primary_role_empty_df(self):
        """Test primary role with empty DataFrame."""
        df = pd.DataFrame()
        
        result = get_employee_primary_role(df)
        assert result == 'Unknown'


class TestEmployeeOvertimeCalculation:
    """Test employee overtime calculation."""
    
    @patch('src.analysis.overtime_analysis.get_standard_shift_hours')
    def test_calculate_employee_overtime_with_overtime(self, mock_shift_hours):
        """Test employee overtime calculation with overtime hours."""
        mock_shift_hours.return_value = 8.0
        
        df = pd.DataFrame({
            FileColumns.FACILITY_STAFF_ROLE_NAME: ['Charge Nurse (LPN)', 'Charge Nurse (LPN)'],
            FileColumns.FACILITY_TOTAL_HOURS: [10.0, 9.0]  # 2 + 1 = 3 hours overtime
        })
        
        result = calculate_employee_overtime(df, '12345', 'John Doe')
        
        assert result is not None
        assert result['employee_id'] == '12345'
        assert result['employee_name'] == 'John Doe'
        assert result['total_overtime_hours'] == 3.0
        assert result['days_with_overtime'] == 2
        assert result['average_daily_overtime'] == 1.5
        assert result['primary_role'] == 'Charge Nurse (LPN)'
    
    @patch('src.analysis.overtime_analysis.get_standard_shift_hours')
    def test_calculate_employee_overtime_no_overtime(self, mock_shift_hours):
        """Test employee overtime calculation with no overtime."""
        mock_shift_hours.return_value = 8.0
        
        df = pd.DataFrame({
            FileColumns.FACILITY_STAFF_ROLE_NAME: ['Charge Nurse (LPN)', 'Charge Nurse (LPN)'],
            FileColumns.FACILITY_TOTAL_HOURS: [8.0, 7.5]  # No overtime
        })
        
        result = calculate_employee_overtime(df, '12345', 'John Doe')
        
        assert result is None


class TestOvertimeAnalysis:
    """Test complete overtime analysis."""
    
    @patch('src.analysis.overtime_analysis.get_standard_shift_hours')
    @patch('src.analysis.overtime_analysis.get_standard_display_name')
    def test_calculate_overtime_analysis_with_data(self, mock_display_name, mock_shift_hours):
        """Test overtime analysis with sample data."""
        mock_shift_hours.return_value = 8.0
        mock_display_name.return_value = 'Charge Nurse (LPN)'
        
        # Create sample facility data
        facility_df = pd.DataFrame({
            FileColumns.FACILITY_EMPLOYEE_ID: ['123', '123', '456', '456'],
            FileColumns.FACILITY_EMPLOYEE_NAME: ['John Doe', 'John Doe', 'Jane Smith', 'Jane Smith'],
            FileColumns.FACILITY_STAFF_ROLE_NAME: ['Charge Nurse (LPN)', 'Charge Nurse (LPN)', 'Certified Nursing Assistant', 'Certified Nursing Assistant'],
            FileColumns.FACILITY_TOTAL_HOURS: [10.0, 9.0, 8.5, 8.0],  # John: 3hrs OT, Jane: 0.5hrs OT
            FileColumns.FACILITY_HOURS_DATE: [datetime.now(), datetime.now(), datetime.now(), datetime.now()]
        })
        
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()
        
        result = calculate_overtime_analysis(
            facility_df=facility_df,
            facility_name='Test Facility',
            analysis_start_date=start_date,
            analysis_end_date=end_date,
            top_count=3
        )
        
        assert isinstance(result, OvertimeAnalysis)
        assert result.facility == 'Test Facility'
        assert result.total_employees_with_overtime == 2
        assert result.top_count_requested == 3
        assert result.total_overtime_hours_facility == 3.5
        assert len(result.top_employees) == 2
        
        # Check top employee is John Doe with 3 hours
        top_employee = result.top_employees[0]
        assert top_employee.employee_name == 'John Doe'
        assert top_employee.total_overtime_hours == 3.0
        assert top_employee.rank == 1
    
    def test_calculate_overtime_analysis_empty_data(self):
        """Test overtime analysis with empty data."""
        facility_df = pd.DataFrame()
        
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()
        
        result = calculate_overtime_analysis(
            facility_df=facility_df,
            facility_name='Test Facility',
            analysis_start_date=start_date,
            analysis_end_date=end_date,
            top_count=3
        )
        
        assert isinstance(result, OvertimeAnalysis)
        assert result.facility == 'Test Facility'
        assert result.total_employees_with_overtime == 0
        assert result.total_overtime_hours_facility == 0.0
        assert len(result.top_employees) == 0


class TestOvertimeDataValidation:
    """Test overtime data validation."""
    
    def test_validate_overtime_data_valid(self):
        """Test validation with valid data."""
        df = pd.DataFrame({
            FileColumns.FACILITY_EMPLOYEE_ID: ['123'],
            FileColumns.FACILITY_EMPLOYEE_NAME: ['John Doe'],
            FileColumns.FACILITY_TOTAL_HOURS: [8.0],
            FileColumns.FACILITY_STAFF_ROLE_NAME: ['Charge Nurse (LPN)'],
            FileColumns.FACILITY_HOURS_DATE: [datetime.now()]
        })
        
        is_valid, missing_columns = validate_overtime_data(df)
        
        assert is_valid is True
        assert len(missing_columns) == 0
    
    def test_validate_overtime_data_missing_columns(self):
        """Test validation with missing columns."""
        df = pd.DataFrame({
            FileColumns.FACILITY_EMPLOYEE_ID: ['123'],
            FileColumns.FACILITY_EMPLOYEE_NAME: ['John Doe']
            # Missing required columns
        })
        
        is_valid, missing_columns = validate_overtime_data(df)
        
        assert is_valid is False
        assert len(missing_columns) > 0
        assert FileColumns.FACILITY_TOTAL_HOURS in missing_columns


class TestOvertimeDataModels:
    """Test overtime data models."""
    
    def test_overtime_employee_model(self):
        """Test OvertimeEmployee data model."""
        employee = OvertimeEmployee(
            employee_id='12345',
            employee_name='John Doe',
            total_overtime_hours=15.5,
            days_with_overtime=3,
            average_daily_overtime=5.17,
            primary_role='Charge Nurse (LPN)',
            rank=1
        )
        
        assert employee.employee_id == '12345'
        assert employee.employee_name == 'John Doe'
        assert employee.total_overtime_hours == 15.5
        assert employee.days_with_overtime == 3
        assert employee.average_daily_overtime == 5.17
        assert employee.primary_role == 'Charge Nurse (LPN)'
        assert employee.rank == 1
    
    def test_overtime_analysis_model(self):
        """Test OvertimeAnalysis data model."""
        employee1 = OvertimeEmployee(
            employee_id='123',
            employee_name='John Doe',
            total_overtime_hours=10.0,
            days_with_overtime=2,
            average_daily_overtime=5.0,
            primary_role='Charge Nurse (LPN)',
            rank=1
        )
        
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()
        
        analysis = OvertimeAnalysis(
            facility='Test Facility',
            top_employees=[employee1],
            total_employees_with_overtime=5,
            top_count_requested=3,
            total_overtime_hours_facility=25.0,
            analysis_period_start=start_date,
            analysis_period_end=end_date
        )
        
        assert analysis.facility == 'Test Facility'
        assert len(analysis.top_employees) == 1
        assert analysis.total_employees_with_overtime == 5
        assert analysis.top_count_requested == 3
        assert analysis.total_overtime_hours_facility == 25.0
        assert analysis.analysis_period_start == start_date
        assert analysis.analysis_period_end == end_date


if __name__ == '__main__':
    pytest.main([__file__])