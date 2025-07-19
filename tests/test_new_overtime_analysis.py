"""
Unit tests for the new overtime analysis module.
Tests overtime calculation based on 40-hour work week threshold.
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from src.analysis.overtime_analysis import analyze_overtime, format_overtime_display
from src.models.data_models import OvertimeResult, EmployeeOvertimeSummary
from config.constants import OVERTIME_THRESHOLD


class TestNewOvertimeAnalysis:
    """Test suite for new overtime analysis functionality"""
    
    @pytest.fixture
    def sample_facility_data(self):
        """Create sample facility data for testing"""
        # Create a week's worth of data
        base_date = datetime(2025, 1, 6)  # Monday
        data = []
        
        # Employee 1: 45 hours total (5 hours overtime)
        for i in range(5):
            data.append({
                'employee_id': 'EMP001',
                'employee_name': 'John Doe',
                'actual_hours': 9.0,  # 9 hours per day for 5 days = 45 hours
                'role': 'Registered Nurse',
                'date': base_date + timedelta(days=i),
                'week_start': base_date
            })
        
        # Employee 2: 38 hours total (no overtime)
        for i in range(5):
            data.append({
                'employee_id': 'EMP002',
                'employee_name': 'Jane Smith',
                'actual_hours': 7.6,  # 7.6 hours per day for 5 days = 38 hours
                'role': 'Licensed Practical Nurse',
                'date': base_date + timedelta(days=i),
                'week_start': base_date
            })
        
        # Employee 3: 50 hours total (10 hours overtime) - split across roles
        for i in range(3):
            data.append({
                'employee_id': 'EMP003',
                'employee_name': 'Bob Wilson',
                'actual_hours': 10.0,  # 30 hours as RN
                'role': 'Registered Nurse',
                'date': base_date + timedelta(days=i),
                'week_start': base_date
            })
        for i in range(3, 5):
            data.append({
                'employee_id': 'EMP003',
                'employee_name': 'Bob Wilson',
                'actual_hours': 10.0,  # 20 hours as Charge Nurse
                'role': 'Charge Nurse',
                'date': base_date + timedelta(days=i),
                'week_start': base_date
            })
        
        return pd.DataFrame(data)
    
    def test_overtime_calculation_basic(self, sample_facility_data):
        """Test basic overtime calculation"""
        result = analyze_overtime(
            facility_df=sample_facility_data,
            facility='Test Facility'
        )
        
        assert isinstance(result, OvertimeResult)
        assert result.facility == 'Test Facility'
        assert result.total_overtime_hours == 15.0  # 5 + 10 hours
        assert result.employee_count == 2  # 2 employees with overtime
        assert len(result.top_overtime_employees) == 2
    
    def test_overtime_employee_sorting(self, sample_facility_data):
        """Test that employees are sorted by overtime hours descending"""
        result = analyze_overtime(
            facility_df=sample_facility_data,
            facility='Test Facility'
        )
        
        # Bob Wilson (10 hours) should be first, John Doe (5 hours) second
        assert result.top_overtime_employees[0].employee_name == 'Bob Wilson'
        assert result.top_overtime_employees[0].overtime_hours == 10.0
        assert result.top_overtime_employees[1].employee_name == 'John Doe'
        assert result.top_overtime_employees[1].overtime_hours == 5.0
    
    def test_primary_role_calculation(self, sample_facility_data):
        """Test that primary role is correctly identified"""
        result = analyze_overtime(
            facility_df=sample_facility_data,
            facility='Test Facility'
        )
        
        # Bob Wilson worked 30 hours as RN and 20 as Charge Nurse
        bob = next(emp for emp in result.top_overtime_employees if emp.employee_name == 'Bob Wilson')
        assert bob.primary_role == 'Registered Nurse'
    
    def test_no_overtime_scenario(self):
        """Test scenario where no employees have overtime"""
        data = pd.DataFrame([
            {
                'employee_id': 'EMP001',
                'employee_name': 'John Doe',
                'actual_hours': 35.0,
                'role': 'Registered Nurse',
                'date': datetime(2025, 1, 6),
                'week_start': datetime(2025, 1, 6)
            }
        ])
        
        result = analyze_overtime(
            facility_df=data,
            facility='Test Facility'
        )
        
        assert result.total_overtime_hours == 0.0
        assert result.employee_count == 0
        assert len(result.top_overtime_employees) == 0
    
    def test_exactly_40_hours(self):
        """Test employee with exactly 40 hours (no overtime)"""
        data = pd.DataFrame([
            {
                'employee_id': 'EMP001',
                'employee_name': 'John Doe',
                'actual_hours': 40.0,
                'role': 'Registered Nurse',
                'date': datetime(2025, 1, 6),
                'week_start': datetime(2025, 1, 6)
            }
        ])
        
        result = analyze_overtime(
            facility_df=data,
            facility='Test Facility'
        )
        
        assert result.total_overtime_hours == 0.0
        assert result.employee_count == 0
    
    def test_date_filtering(self, sample_facility_data):
        """Test date range filtering"""
        # Add data from a different week
        extra_data = pd.DataFrame([
            {
                'employee_id': 'EMP004',
                'employee_name': 'Alice Brown',
                'actual_hours': 50.0,
                'role': 'Registered Nurse',
                'date': datetime(2025, 1, 13),  # Next week
                'week_start': datetime(2025, 1, 13)
            }
        ])
        
        combined_data = pd.concat([sample_facility_data, extra_data], ignore_index=True)
        
        # Filter to only first week
        result = analyze_overtime(
            facility_df=combined_data,
            facility='Test Facility',
            week_start_date=datetime(2025, 1, 6),
            week_end_date=datetime(2025, 1, 10)
        )
        
        # Should not include Alice Brown's overtime
        assert result.employee_count == 2  # Only Bob and John
        assert all(emp.employee_name != 'Alice Brown' for emp in result.top_overtime_employees)
    
    def test_format_overtime_display(self, sample_facility_data):
        """Test formatting of overtime results for display"""
        result = analyze_overtime(
            facility_df=sample_facility_data,
            facility='Test Facility'
        )
        
        formatted = format_overtime_display(result)
        
        assert formatted['facility'] == 'Test Facility'
        assert formatted['total_overtime_hours'] == '15.0'
        assert formatted['employee_count'] == 2
        assert len(formatted['top_employees']) == 2
        
        # Check first employee formatting
        first_emp = formatted['top_employees'][0]
        assert first_emp['name'] == 'Bob Wilson'
        assert first_emp['total_hours'] == '50.0'
        assert first_emp['overtime_hours'] == '10.0'
        assert first_emp['primary_role'] == 'Registered Nurse'
    
    def test_empty_dataframe(self):
        """Test handling of empty dataframe"""
        empty_df = pd.DataFrame()
        
        result = analyze_overtime(
            facility_df=empty_df,
            facility='Test Facility'
        )
        
        assert result.total_overtime_hours == 0.0
        assert result.employee_count == 0
        assert len(result.top_overtime_employees) == 0
    
    def test_top_n_limit(self):
        """Test that only top N employees are returned based on configuration"""
        # Create data with 5 employees having overtime
        data = []
        base_date = datetime(2025, 1, 6)
        
        for i in range(5):
            data.append({
                'employee_id': f'EMP{i:03d}',
                'employee_name': f'Employee {i}',
                'actual_hours': 40.0 + (i + 1) * 2,  # 42, 44, 46, 48, 50 hours
                'role': 'Registered Nurse',
                'date': base_date,
                'week_start': base_date
            })
        
        df = pd.DataFrame(data)
        result = analyze_overtime(
            facility_df=df,
            facility='Test Facility'
        )
        
        # Should only return top 3 based on REPORT_TOP_OVERTIME_COUNT
        assert len(result.top_overtime_employees) == 3
        # Should be sorted by overtime hours descending
        assert result.top_overtime_employees[0].overtime_hours == 10.0  # Employee 4
        assert result.top_overtime_employees[1].overtime_hours == 8.0   # Employee 3
        assert result.top_overtime_employees[2].overtime_hours == 6.0   # Employee 2
    
    def test_overtime_calculation_edge_cases(self):
        """Test edge cases in overtime calculation"""
        data = pd.DataFrame([
            {
                'employee_id': 'EMP001',
                'employee_name': 'John Doe',
                'actual_hours': 100.0,  # Extreme overtime
                'role': 'Registered Nurse',
                'date': datetime(2025, 1, 6),
                'week_start': datetime(2025, 1, 6)
            },
            {
                'employee_id': 'EMP002',
                'employee_name': 'Jane Smith',
                'actual_hours': 0.5,  # Very low hours
                'role': 'Licensed Practical Nurse',
                'date': datetime(2025, 1, 6),
                'week_start': datetime(2025, 1, 6)
            }
        ])
        
        result = analyze_overtime(
            facility_df=data,
            facility='Test Facility'
        )
        
        assert result.total_overtime_hours == 60.0  # 100 - 40
        assert result.employee_count == 1
        assert result.top_overtime_employees[0].overtime_hours == 60.0
    
    def test_overtime_threshold_value(self):
        """Test that overtime threshold is correctly set to 40 hours"""
        assert OVERTIME_THRESHOLD == 40.0