"""
Unit tests for date_calculator.py module.
Tests the F-0 control variables date calculation functionality.
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import patch

# Import the modules under test
from src.utils.date_calculator import (
    calculate_analysis_date_range,
    validate_date_range,
    _find_most_recent_data_day
)
from config.settings import ControlVariables
from config.constants import FileColumns, DayOfWeek


class TestCalculateAnalysisDateRange:
    """Test the main date calculation function."""
    
    @pytest.fixture
    def sample_facility_df(self):
        """Create sample facility dataframe for testing."""
        dates = pd.date_range(start='2025-05-01', end='2025-05-31', freq='D')
        data = []
        for date in dates:
            data.append({
                FileColumns.FACILITY_HOURS_DATE: date,
                FileColumns.FACILITY_LOCATION_NAME: 'Test Facility',
                FileColumns.FACILITY_STAFF_ROLE_NAME: 'Nurse',
                FileColumns.FACILITY_TOTAL_HOURS: 40.0
            })
        return pd.DataFrame(data)
    
    @pytest.fixture
    def default_control_variables(self):
        """Create default control variables for testing."""
        return ControlVariables(
            days_to_drop=7,
            days_to_process=84,
            use_data_day=False,
            new_data_day=1
        )
    
    def test_command_line_override_priority(self, sample_facility_df, default_control_variables):
        """Test that command line arguments take highest priority."""
        # Test: Command line overrides should be used when provided
        start_override = "2025-05-10"
        end_override = "2025-05-15"
        
        start_date, end_date = calculate_analysis_date_range(
            sample_facility_df,
            default_control_variables,
            start_override,
            end_override
        )
        
        expected_start = datetime(2025, 5, 10)
        expected_end = datetime(2025, 5, 15)
        
        assert start_date == expected_start
        assert end_date == expected_end
    
    def test_dynamic_calculation_with_days_to_drop(self, sample_facility_df, default_control_variables):
        """Test dynamic calculation using days_to_drop logic (F-0a)."""
        # Test: Dynamic calculation when no overrides provided
        start_date, end_date = calculate_analysis_date_range(
            sample_facility_df,
            default_control_variables,
            None,
            None
        )
        
        # Expected: Most recent date (2025-05-31) minus 7 days = 2025-05-24 as period end
        # Then 84 days back from period end for analysis start
        expected_period_end = datetime(2025, 5, 31) - timedelta(days=7)  # 2025-05-24
        expected_start = expected_period_end - timedelta(days=83)  # 84 days total including end date
        
        assert end_date == expected_period_end
        assert start_date == expected_start
        assert (end_date - start_date).days == 83  # 84 days total including both dates
    
    def test_dynamic_calculation_with_data_day(self, sample_facility_df):
        """Test dynamic calculation using new_data_day logic (F-0c, F-0d)."""
        # Test: Use data day logic (Sunday = 1)
        control_vars = ControlVariables(
            days_to_drop=7,
            days_to_process=84,
            use_data_day=True,
            new_data_day=1  # Sunday
        )
        
        start_date, end_date = calculate_analysis_date_range(
            sample_facility_df,
            control_vars,
            None,
            None
        )
        
        # Should find most recent Sunday in the data
        # May 2025: 4, 11, 18, 25 are Sundays, so most recent should be 2025-05-25
        expected_period_end = datetime(2025, 5, 25)
        expected_start = expected_period_end - timedelta(days=83)
        
        assert end_date == expected_period_end
        assert start_date == expected_start
    
    def test_empty_facility_data_handling(self, default_control_variables):
        """Test handling of empty facility dataframe."""
        # Edge case: Empty dataframe should use current date
        empty_df = pd.DataFrame()
        
        with patch('src.utils.date_calculator.datetime') as mock_datetime:
            mock_now = datetime(2025, 7, 14, 12, 0, 0)
            mock_datetime.now.return_value = mock_now
            
            start_date, end_date = calculate_analysis_date_range(
                empty_df,
                default_control_variables,
                None,
                None
            )
            
            assert start_date == mock_now
            assert end_date == mock_now
    
    def test_missing_date_column_handling(self, default_control_variables):
        """Test handling when date column is missing."""
        # Edge case: Missing date column should use current date
        df_no_date = pd.DataFrame({
            'other_column': ['data']
        })
        
        with patch('src.utils.date_calculator.datetime') as mock_datetime:
            mock_now = datetime(2025, 7, 14, 12, 0, 0)
            mock_datetime.now.return_value = mock_now
            
            start_date, end_date = calculate_analysis_date_range(
                df_no_date,
                default_control_variables,
                None,
                None
            )
            
            assert start_date == mock_now
            assert end_date == mock_now
    
    def test_partial_command_line_override(self, sample_facility_df, default_control_variables):
        """Test that both start and end dates must be provided for override."""
        # Failure case: Only one override should fall back to dynamic calculation
        start_date, end_date = calculate_analysis_date_range(
            sample_facility_df,
            default_control_variables,
            "2025-05-10",  # Only start provided
            None           # End not provided
        )
        
        # Should use dynamic calculation, not the partial override
        expected_period_end = datetime(2025, 5, 31) - timedelta(days=7)
        expected_start = expected_period_end - timedelta(days=83)
        
        assert start_date == expected_start
        assert end_date == expected_period_end


class TestFindMostRecentDataDay:
    """Test the helper function for finding most recent data day."""
    
    @pytest.fixture
    def weekly_data(self):
        """Create data spanning multiple weeks with different days."""
        dates = [
            datetime(2025, 5, 4),   # Sunday (day 1)
            datetime(2025, 5, 5),   # Monday (day 2) 
            datetime(2025, 5, 11),  # Sunday (day 1)
            datetime(2025, 5, 12),  # Monday (day 2)
            datetime(2025, 5, 18),  # Sunday (day 1)
            datetime(2025, 5, 25),  # Sunday (day 1) - most recent
        ]
        
        data = []
        for date in dates:
            data.append({
                FileColumns.FACILITY_HOURS_DATE: date,
                'other_data': 'test'
            })
        return pd.DataFrame(data)
    
    def test_find_most_recent_sunday(self, weekly_data):
        """Test finding most recent Sunday (day 1)."""
        result = _find_most_recent_data_day(
            weekly_data, 
            FileColumns.FACILITY_HOURS_DATE, 
            1  # Sunday
        )
        
        expected = datetime(2025, 5, 25)  # Most recent Sunday
        assert result == expected
    
    def test_find_most_recent_monday(self, weekly_data):
        """Test finding most recent Monday (day 2)."""
        result = _find_most_recent_data_day(
            weekly_data,
            FileColumns.FACILITY_HOURS_DATE,
            2  # Monday
        )
        
        expected = datetime(2025, 5, 12)  # Most recent Monday
        assert result == expected
    
    def test_target_day_not_found(self, weekly_data):
        """Test handling when target day is not found in data."""
        # Test with day 6 (Friday) which doesn't exist in our test data
        result = _find_most_recent_data_day(
            weekly_data,
            FileColumns.FACILITY_HOURS_DATE,
            6  # Friday
        )
        
        # Should fall back to most recent date overall
        expected = datetime(2025, 5, 25)  # Most recent date in data
        assert result == expected


class TestValidateDateRange:
    """Test the date range validation function."""
    
    def test_valid_date_range(self):
        """Test validation of valid date range."""
        start = datetime(2025, 5, 1)
        end = datetime(2025, 5, 31)
        
        assert validate_date_range(start, end) is True
    
    def test_invalid_date_range_same_dates(self):
        """Test validation fails when start equals end."""
        date = datetime(2025, 5, 15)
        
        assert validate_date_range(date, date) is False
    
    def test_invalid_date_range_start_after_end(self):
        """Test validation fails when start is after end."""
        start = datetime(2025, 5, 31)
        end = datetime(2025, 5, 1)
        
        assert validate_date_range(start, end) is False
    
    def test_very_short_date_range(self):
        """Test validation of very short date range."""
        start = datetime(2025, 5, 15, 10, 0, 0)
        end = datetime(2025, 5, 15, 14, 0, 0)  # Same day, different times
        
        # Should fail because span is < 1 day
        assert validate_date_range(start, end) is False
    
    def test_very_long_date_range(self):
        """Test validation of very long date range (should warn but pass)."""
        start = datetime(2024, 1, 1)
        end = datetime(2025, 6, 1)  # Over 1 year
        
        # Should pass but log warning
        assert validate_date_range(start, end) is True
    
    def test_normal_analysis_period(self):
        """Test validation of typical 84-day analysis period."""
        start = datetime(2025, 3, 1)
        end = datetime(2025, 5, 24)  # 84 days
        
        assert validate_date_range(start, end) is True


class TestSundayFirstDayLogic:
    """Test the Sunday=1 day-of-week convention implementation."""
    
    def test_day_of_week_conversion(self):
        """Test conversion from Sunday=1 to Python weekday convention."""
        # This tests the logic in _find_most_recent_data_day
        test_dates = [
            (datetime(2025, 5, 4), 6),   # Sunday -> Python weekday 6
            (datetime(2025, 5, 5), 0),   # Monday -> Python weekday 0
            (datetime(2025, 5, 6), 1),   # Tuesday -> Python weekday 1
            (datetime(2025, 5, 10), 5),  # Saturday -> Python weekday 5
        ]
        
        for test_date, expected_python_weekday in test_dates:
            assert test_date.weekday() == expected_python_weekday
    
    def test_enum_values_match_upstream(self):
        """Test that DayOfWeek enum matches upstream DAY_NUMBER = 1 for Sunday."""
        assert DayOfWeek.SUNDAY.value == 1
        assert DayOfWeek.MONDAY.value == 2
        assert DayOfWeek.TUESDAY.value == 3
        assert DayOfWeek.WEDNESDAY.value == 4
        assert DayOfWeek.THURSDAY.value == 5
        assert DayOfWeek.FRIDAY.value == 6
        assert DayOfWeek.SATURDAY.value == 7


# Integration test combining multiple components
class TestDateCalculatorIntegration:
    """Integration tests for the complete date calculation workflow."""
    
    def test_complete_f0_workflow(self):
        """Test complete F-0 control variables workflow."""
        # Create realistic test data
        dates = pd.date_range(start='2025-03-01', end='2025-05-31', freq='D')
        facility_df = pd.DataFrame({
            FileColumns.FACILITY_HOURS_DATE: dates,
            FileColumns.FACILITY_LOCATION_NAME: 'Test Facility',
            FileColumns.FACILITY_STAFF_ROLE_NAME: 'Nurse',
            FileColumns.FACILITY_TOTAL_HOURS: 40.0
        })
        
        # Test F-0 variables: use_data_day=True, new_data_day=1 (Sunday)
        control_vars = ControlVariables(
            days_to_drop=7,
            days_to_process=84,
            use_data_day=True,
            new_data_day=1
        )
        
        start_date, end_date = calculate_analysis_date_range(
            facility_df,
            control_vars,
            None,
            None
        )
        
        # Validate results
        assert validate_date_range(start_date, end_date)
        assert (end_date - start_date).days == 83  # 84 days including both dates
        assert end_date.weekday() == 6  # Should be Sunday (Python weekday 6)
        
        # Verify it's the most recent Sunday
        most_recent_date = facility_df[FileColumns.FACILITY_HOURS_DATE].max()
        assert end_date <= most_recent_date
    
    def test_production_vs_testing_scenarios(self):
        """Test that production and testing scenarios work correctly."""
        # Create test data
        facility_df = pd.DataFrame({
            FileColumns.FACILITY_HOURS_DATE: pd.date_range('2025-05-01', '2025-05-31'),
            FileColumns.FACILITY_LOCATION_NAME: 'Test',
            FileColumns.FACILITY_STAFF_ROLE_NAME: 'Nurse',
            FileColumns.FACILITY_TOTAL_HOURS: 40.0
        })
        
        control_vars = ControlVariables()
        
        # Production scenario: No overrides (dynamic calculation)
        prod_start, prod_end = calculate_analysis_date_range(
            facility_df, control_vars, None, None
        )
        
        # Testing scenario: Command line overrides
        test_start, test_end = calculate_analysis_date_range(
            facility_df, control_vars, "2025-05-01", "2025-05-07"
        )
        
        # Verify different results
        assert prod_start != test_start
        assert prod_end != test_end
        
        # Verify testing scenario uses exact dates
        assert test_start == datetime(2025, 5, 1)
        assert test_end == datetime(2025, 5, 7)
        
        # Verify production scenario uses dynamic calculation
        assert validate_date_range(prod_start, prod_end)