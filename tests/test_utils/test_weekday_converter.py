"""
Unit tests for weekday converter utility module.

Tests cover all conversion functions with expected use cases, edge cases, and failure scenarios.
"""

import pytest
from datetime import date, datetime
from src.utils.weekday_converter import (
    model_to_python_weekday,
    python_weekday_to_model,
    model_to_sunday_first,
    sunday_first_to_model,
    python_weekday_to_sunday_first,
    sunday_first_to_python_weekday,
    get_weekday_name,
    convert_weekday_list,
    weekday_from_date,
)
from config.constants import DayOfWeek


class TestModelToPythonWeekday:
    """Test conversion from model format (Sunday=1) to Python weekday (Monday=0)."""
    
    def test_model_to_python_expected_use(self):
        """Test expected use cases for model to Python conversion."""
        # Test all days of the week
        assert model_to_python_weekday(1) == 6  # Sunday
        assert model_to_python_weekday(2) == 0  # Monday
        assert model_to_python_weekday(3) == 1  # Tuesday
        assert model_to_python_weekday(4) == 2  # Wednesday
        assert model_to_python_weekday(5) == 3  # Thursday
        assert model_to_python_weekday(6) == 4  # Friday
        assert model_to_python_weekday(7) == 5  # Saturday
    
    def test_model_to_python_with_enum(self):
        """Test conversion using DayOfWeek enum."""
        assert model_to_python_weekday(DayOfWeek.SUNDAY) == 6
        assert model_to_python_weekday(DayOfWeek.MONDAY) == 0
        assert model_to_python_weekday(DayOfWeek.FRIDAY) == 4
    
    def test_model_to_python_edge_cases(self):
        """Test edge cases (boundary values)."""
        # Test boundary values
        assert model_to_python_weekday(1) == 6  # Minimum valid value
        assert model_to_python_weekday(7) == 5  # Maximum valid value
    
    def test_model_to_python_failure_cases(self):
        """Test failure cases with invalid input."""
        with pytest.raises(ValueError, match="Invalid model day number"):
            model_to_python_weekday(0)
        
        with pytest.raises(ValueError, match="Invalid model day number"):
            model_to_python_weekday(8)
        
        with pytest.raises(ValueError, match="Invalid model day number"):
            model_to_python_weekday(-1)


class TestPythonWeekdayToModel:
    """Test conversion from Python weekday (Monday=0) to model format (Sunday=1)."""
    
    def test_python_to_model_expected_use(self):
        """Test expected use cases for Python to model conversion."""
        # Test all days of the week
        assert python_weekday_to_model(0) == 2  # Monday
        assert python_weekday_to_model(1) == 3  # Tuesday
        assert python_weekday_to_model(2) == 4  # Wednesday
        assert python_weekday_to_model(3) == 5  # Thursday
        assert python_weekday_to_model(4) == 6  # Friday
        assert python_weekday_to_model(5) == 7  # Saturday
        assert python_weekday_to_model(6) == 1  # Sunday
    
    def test_python_to_model_edge_cases(self):
        """Test edge cases (boundary values)."""
        # Test boundary values
        assert python_weekday_to_model(0) == 2  # Minimum valid value
        assert python_weekday_to_model(6) == 1  # Maximum valid value
    
    def test_python_to_model_failure_cases(self):
        """Test failure cases with invalid input."""
        with pytest.raises(ValueError, match="Invalid Python weekday number"):
            python_weekday_to_model(-1)
        
        with pytest.raises(ValueError, match="Invalid Python weekday number"):
            python_weekday_to_model(7)


class TestModelToSundayFirst:
    """Test conversion from model format (Sunday=1) to Sunday-first indexing (Sunday=0)."""
    
    def test_model_to_sunday_first_expected_use(self):
        """Test expected use cases for model to Sunday-first conversion."""
        # Test all days of the week
        assert model_to_sunday_first(1) == 0  # Sunday
        assert model_to_sunday_first(2) == 1  # Monday
        assert model_to_sunday_first(3) == 2  # Tuesday
        assert model_to_sunday_first(4) == 3  # Wednesday
        assert model_to_sunday_first(5) == 4  # Thursday
        assert model_to_sunday_first(6) == 5  # Friday
        assert model_to_sunday_first(7) == 6  # Saturday
    
    def test_model_to_sunday_first_with_enum(self):
        """Test conversion using DayOfWeek enum."""
        assert model_to_sunday_first(DayOfWeek.SUNDAY) == 0
        assert model_to_sunday_first(DayOfWeek.WEDNESDAY) == 3
        assert model_to_sunday_first(DayOfWeek.SATURDAY) == 6
    
    def test_model_to_sunday_first_failure_cases(self):
        """Test failure cases with invalid input."""
        with pytest.raises(ValueError, match="Invalid model day number"):
            model_to_sunday_first(0)
        
        with pytest.raises(ValueError, match="Invalid model day number"):
            model_to_sunday_first(8)


class TestSundayFirstToModel:
    """Test conversion from Sunday-first indexing (Sunday=0) to model format (Sunday=1)."""
    
    def test_sunday_first_to_model_expected_use(self):
        """Test expected use cases for Sunday-first to model conversion."""
        # Test all days of the week
        assert sunday_first_to_model(0) == 1  # Sunday
        assert sunday_first_to_model(1) == 2  # Monday
        assert sunday_first_to_model(2) == 3  # Tuesday
        assert sunday_first_to_model(3) == 4  # Wednesday
        assert sunday_first_to_model(4) == 5  # Thursday
        assert sunday_first_to_model(5) == 6  # Friday
        assert sunday_first_to_model(6) == 7  # Saturday
    
    def test_sunday_first_to_model_failure_cases(self):
        """Test failure cases with invalid input."""
        with pytest.raises(ValueError, match="Invalid Sunday-first day number"):
            sunday_first_to_model(-1)
        
        with pytest.raises(ValueError, match="Invalid Sunday-first day number"):
            sunday_first_to_model(7)


class TestPythonToSundayFirstConversion:
    """Test conversion between Python weekday and Sunday-first indexing."""
    
    def test_python_to_sunday_first_expected_use(self):
        """Test expected use cases for Python to Sunday-first conversion."""
        assert python_weekday_to_sunday_first(0) == 1  # Monday
        assert python_weekday_to_sunday_first(6) == 0  # Sunday
    
    def test_sunday_first_to_python_expected_use(self):
        """Test expected use cases for Sunday-first to Python conversion."""
        assert sunday_first_to_python_weekday(0) == 6  # Sunday
        assert sunday_first_to_python_weekday(1) == 0  # Monday


class TestGetWeekdayName:
    """Test weekday name retrieval function."""
    
    def test_get_weekday_name_model_format(self):
        """Test getting weekday names from model format."""
        assert get_weekday_name(1, "model") == "SUNDAY"
        assert get_weekday_name(2, "model") == "MONDAY"
        assert get_weekday_name(7, "model") == "SATURDAY"
    
    def test_get_weekday_name_python_format(self):
        """Test getting weekday names from Python format."""
        assert get_weekday_name(0, "python") == "MONDAY"
        assert get_weekday_name(6, "python") == "SUNDAY"
    
    def test_get_weekday_name_sunday_first_format(self):
        """Test getting weekday names from Sunday-first format."""
        assert get_weekday_name(0, "sunday_first") == "SUNDAY"
        assert get_weekday_name(1, "sunday_first") == "MONDAY"
    
    def test_get_weekday_name_with_enum(self):
        """Test getting weekday names with DayOfWeek enum."""
        assert get_weekday_name(DayOfWeek.FRIDAY, "model") == "FRIDAY"
    
    def test_get_weekday_name_failure_cases(self):
        """Test failure cases with invalid format or day."""
        with pytest.raises(ValueError, match="Invalid format_type"):
            get_weekday_name(1, "invalid")
        
        with pytest.raises(ValueError, match="Invalid day number"):
            get_weekday_name(8, "model")


class TestConvertWeekdayList:
    """Test batch weekday list conversion function."""
    
    def test_convert_weekday_list_model_to_python(self):
        """Test converting list from model to Python format."""
        result = convert_weekday_list([1, 2, 3], "model", "python")
        assert result == [6, 0, 1]
    
    def test_convert_weekday_list_python_to_sunday_first(self):
        """Test converting list from Python to Sunday-first format."""
        result = convert_weekday_list([0, 1, 6], "python", "sunday_first")
        assert result == [1, 2, 0]
    
    def test_convert_weekday_list_same_format(self):
        """Test converting list to the same format (should return copy)."""
        original = [1, 2, 3]
        result = convert_weekday_list(original, "model", "model")
        assert result == original
        assert result is not original  # Should be a copy
    
    def test_convert_weekday_list_failure_cases(self):
        """Test failure cases with invalid formats."""
        with pytest.raises(ValueError, match="Invalid format combination"):
            convert_weekday_list([1, 2], "invalid", "model")


class TestWeekdayFromDate:
    """Test weekday extraction from datetime objects."""
    
    def test_weekday_from_date_model_format(self):
        """Test extracting weekday from date in model format."""
        # Tuesday, July 15, 2025
        test_date = date(2025, 7, 15)
        assert weekday_from_date(test_date, "model") == 3
    
    def test_weekday_from_date_python_format(self):
        """Test extracting weekday from date in Python format."""
        # Tuesday, July 15, 2025
        test_date = date(2025, 7, 15)
        assert weekday_from_date(test_date, "python") == 1
    
    def test_weekday_from_date_sunday_first_format(self):
        """Test extracting weekday from date in Sunday-first format."""
        # Tuesday, July 15, 2025
        test_date = date(2025, 7, 15)
        assert weekday_from_date(test_date, "sunday_first") == 2
    
    def test_weekday_from_date_with_datetime(self):
        """Test extracting weekday from datetime object."""
        # Sunday, July 13, 2025
        test_datetime = datetime(2025, 7, 13, 15, 30, 0)
        assert weekday_from_date(test_datetime, "model") == 1
        assert weekday_from_date(test_datetime, "python") == 6
        assert weekday_from_date(test_datetime, "sunday_first") == 0
    
    def test_weekday_from_date_failure_cases(self):
        """Test failure cases with invalid format."""
        test_date = date(2025, 7, 15)
        with pytest.raises(ValueError, match="Invalid format_type"):
            weekday_from_date(test_date, "invalid")


class TestConversionConsistency:
    """Test that conversions are consistent and reversible."""
    
    def test_model_python_roundtrip(self):
        """Test that model->Python->model conversion is consistent."""
        for model_day in range(1, 8):
            python_day = model_to_python_weekday(model_day)
            back_to_model = python_weekday_to_model(python_day)
            assert back_to_model == model_day
    
    def test_model_sunday_first_roundtrip(self):
        """Test that model->Sunday-first->model conversion is consistent."""
        for model_day in range(1, 8):
            sunday_first_day = model_to_sunday_first(model_day)
            back_to_model = sunday_first_to_model(sunday_first_day)
            assert back_to_model == model_day
    
    def test_python_sunday_first_roundtrip(self):
        """Test that Python->Sunday-first->Python conversion is consistent."""
        for python_day in range(7):
            sunday_first_day = python_weekday_to_sunday_first(python_day)
            back_to_python = sunday_first_to_python_weekday(sunday_first_day)
            assert back_to_python == python_day
    
    def test_date_consistency(self):
        """Test that date-based conversions are consistent."""
        # Test a known date: Tuesday, July 15, 2025
        test_date = date(2025, 7, 15)
        
        # Get weekday in all formats
        model_day = weekday_from_date(test_date, "model")
        python_day = weekday_from_date(test_date, "python")
        sunday_first_day = weekday_from_date(test_date, "sunday_first")
        
        # Verify consistency with direct conversions
        assert model_to_python_weekday(model_day) == python_day
        assert model_to_sunday_first(model_day) == sunday_first_day
        assert python_weekday_to_sunday_first(python_day) == sunday_first_day


class TestExampleScenarios:
    """Test real-world usage scenarios."""
    
    def test_facility_data_processing_scenario(self):
        """Test a scenario where facility data with Python weekdays needs model conversion."""
        # Facility data has dates that resolve to Python weekdays
        python_weekdays = [0, 1, 2, 3, 4]  # Monday through Friday
        
        # Convert to model format for comparison with model data
        model_weekdays = convert_weekday_list(python_weekdays, "python", "model")
        expected_model = [2, 3, 4, 5, 6]  # Monday through Friday in model format
        
        assert model_weekdays == expected_model
    
    def test_weekly_aggregation_scenario(self):
        """Test a scenario for weekly aggregation with Sunday-first indexing."""
        # Model data days for a full week
        model_week = [1, 2, 3, 4, 5, 6, 7]  # Sunday through Saturday
        
        # Convert to Sunday-first indexing for array indexing
        sunday_first_indices = convert_weekday_list(model_week, "model", "sunday_first")
        expected_indices = [0, 1, 2, 3, 4, 5, 6]
        
        assert sunday_first_indices == expected_indices
    
    def test_control_limit_calculation_scenario(self):
        """Test weekday conversion for control limit calculations."""
        # Get model day from a specific date
        analysis_date = date(2025, 7, 14)  # Monday
        model_day = weekday_from_date(analysis_date, "model")
        
        # Verify it's Monday in model format
        assert model_day == 2
        assert get_weekday_name(model_day, "model") == "MONDAY"