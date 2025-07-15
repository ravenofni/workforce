"""
Weekday conversion utilities for workforce analytics.

This module provides functions to convert between different weekday numbering systems:
1. Model data format (Sunday=1, Monday=2, ..., Saturday=7) - used by upstream data
2. Python datetime.weekday() (Monday=0, Tuesday=1, ..., Sunday=6)
3. Internal Sunday-first indexing (Sunday=0, Monday=1, ..., Saturday=6)

The module ensures consistent weekday handling across the codebase when dealing with
different data sources and Python's datetime library.
"""

from typing import Union, List, Dict
from datetime import datetime
import logging

from config.constants import DayOfWeek


logger = logging.getLogger(__name__)


# Conversion mappings for quick lookup
MODEL_TO_PYTHON_WEEKDAY: Dict[int, int] = {
    1: 6,  # Sunday -> 6
    2: 0,  # Monday -> 0
    3: 1,  # Tuesday -> 1
    4: 2,  # Wednesday -> 2
    5: 3,  # Thursday -> 3
    6: 4,  # Friday -> 4
    7: 5,  # Saturday -> 5
}

PYTHON_WEEKDAY_TO_MODEL: Dict[int, int] = {
    0: 2,  # Monday -> 2
    1: 3,  # Tuesday -> 3
    2: 4,  # Wednesday -> 4
    3: 5,  # Thursday -> 5
    4: 6,  # Friday -> 6
    5: 7,  # Saturday -> 7
    6: 1,  # Sunday -> 1
}

MODEL_TO_SUNDAY_FIRST: Dict[int, int] = {
    1: 0,  # Sunday -> 0
    2: 1,  # Monday -> 1
    3: 2,  # Tuesday -> 2
    4: 3,  # Wednesday -> 3
    5: 4,  # Thursday -> 4
    6: 5,  # Friday -> 5
    7: 6,  # Saturday -> 6
}

SUNDAY_FIRST_TO_MODEL: Dict[int, int] = {
    0: 1,  # Sunday -> 1
    1: 2,  # Monday -> 2
    2: 3,  # Tuesday -> 3
    3: 4,  # Wednesday -> 4
    4: 5,  # Thursday -> 5
    5: 6,  # Friday -> 6
    6: 7,  # Saturday -> 7
}


def model_to_python_weekday(model_day: Union[int, DayOfWeek]) -> int:
    """
    Convert model data weekday (Sunday=1) to Python datetime.weekday() format (Monday=0).
    
    Args:
        model_day: Day number in model format (1-7) or DayOfWeek enum
        
    Returns:
        Python weekday number (0-6)
        
    Raises:
        ValueError: If model_day is not in valid range (1-7)
        
    Examples:
        >>> model_to_python_weekday(1)  # Sunday
        6
        >>> model_to_python_weekday(2)  # Monday
        0
        >>> model_to_python_weekday(DayOfWeek.FRIDAY)
        4
    """
    if isinstance(model_day, DayOfWeek):
        model_day = model_day.value
    
    if model_day not in MODEL_TO_PYTHON_WEEKDAY:
        raise ValueError(f"Invalid model day number: {model_day}. Must be 1-7.")
    
    return MODEL_TO_PYTHON_WEEKDAY[model_day]


def python_weekday_to_model(python_day: int) -> int:
    """
    Convert Python datetime.weekday() format (Monday=0) to model data weekday (Sunday=1).
    
    Args:
        python_day: Python weekday number (0-6)
        
    Returns:
        Day number in model format (1-7)
        
    Raises:
        ValueError: If python_day is not in valid range (0-6)
        
    Examples:
        >>> python_weekday_to_model(0)  # Monday
        2
        >>> python_weekday_to_model(6)  # Sunday
        1
        >>> from datetime import date
        >>> python_weekday_to_model(date(2025, 7, 15).weekday())  # Tuesday
        3
    """
    if python_day not in PYTHON_WEEKDAY_TO_MODEL:
        raise ValueError(f"Invalid Python weekday number: {python_day}. Must be 0-6.")
    
    return PYTHON_WEEKDAY_TO_MODEL[python_day]


def model_to_sunday_first(model_day: Union[int, DayOfWeek]) -> int:
    """
    Convert model data weekday (Sunday=1) to Sunday-first indexing (Sunday=0).
    
    Args:
        model_day: Day number in model format (1-7) or DayOfWeek enum
        
    Returns:
        Day number in Sunday-first format (0-6)
        
    Raises:
        ValueError: If model_day is not in valid range (1-7)
        
    Examples:
        >>> model_to_sunday_first(1)  # Sunday
        0
        >>> model_to_sunday_first(7)  # Saturday
        6
        >>> model_to_sunday_first(DayOfWeek.WEDNESDAY)
        3
    """
    if isinstance(model_day, DayOfWeek):
        model_day = model_day.value
    
    if model_day not in MODEL_TO_SUNDAY_FIRST:
        raise ValueError(f"Invalid model day number: {model_day}. Must be 1-7.")
    
    return MODEL_TO_SUNDAY_FIRST[model_day]


def sunday_first_to_model(sunday_day: int) -> int:
    """
    Convert Sunday-first indexing (Sunday=0) to model data weekday (Sunday=1).
    
    Args:
        sunday_day: Day number in Sunday-first format (0-6)
        
    Returns:
        Day number in model format (1-7)
        
    Raises:
        ValueError: If sunday_day is not in valid range (0-6)
        
    Examples:
        >>> sunday_first_to_model(0)  # Sunday
        1
        >>> sunday_first_to_model(6)  # Saturday
        7
    """
    if sunday_day not in SUNDAY_FIRST_TO_MODEL:
        raise ValueError(f"Invalid Sunday-first day number: {sunday_day}. Must be 0-6.")
    
    return SUNDAY_FIRST_TO_MODEL[sunday_day]


def python_weekday_to_sunday_first(python_day: int) -> int:
    """
    Convert Python datetime.weekday() format (Monday=0) to Sunday-first indexing (Sunday=0).
    
    Args:
        python_day: Python weekday number (0-6)
        
    Returns:
        Day number in Sunday-first format (0-6)
        
    Examples:
        >>> python_weekday_to_sunday_first(0)  # Monday
        1
        >>> python_weekday_to_sunday_first(6)  # Sunday
        0
    """
    # Reason: Two-step conversion through model format ensures consistency
    # Python -> Model -> Sunday-first
    model_day = python_weekday_to_model(python_day)
    return model_to_sunday_first(model_day)


def sunday_first_to_python_weekday(sunday_day: int) -> int:
    """
    Convert Sunday-first indexing (Sunday=0) to Python datetime.weekday() format (Monday=0).
    
    Args:
        sunday_day: Day number in Sunday-first format (0-6)
        
    Returns:
        Python weekday number (0-6)
        
    Examples:
        >>> sunday_first_to_python_weekday(0)  # Sunday
        6
        >>> sunday_first_to_python_weekday(1)  # Monday
        0
    """
    # Reason: Two-step conversion through model format ensures consistency
    # Sunday-first -> Model -> Python
    model_day = sunday_first_to_model(sunday_day)
    return model_to_python_weekday(model_day)


def get_weekday_name(day: Union[int, DayOfWeek], format_type: str = "model") -> str:
    """
    Get the name of a weekday given its number in a specific format.
    
    Args:
        day: Day number or DayOfWeek enum
        format_type: The format of the input day number ("model", "python", or "sunday_first")
        
    Returns:
        Weekday name as string
        
    Raises:
        ValueError: If format_type is invalid or day is out of range
        
    Examples:
        >>> get_weekday_name(1, "model")
        'SUNDAY'
        >>> get_weekday_name(0, "python")
        'MONDAY'
        >>> get_weekday_name(0, "sunday_first")
        'SUNDAY'
    """
    # Convert to model format first for consistency
    if format_type == "model":
        model_day = day
    elif format_type == "python":
        model_day = python_weekday_to_model(day)
    elif format_type == "sunday_first":
        model_day = sunday_first_to_model(day)
    else:
        raise ValueError(f"Invalid format_type: {format_type}. Must be 'model', 'python', or 'sunday_first'.")
    
    # Use DayOfWeek enum to get the name
    try:
        return DayOfWeek(model_day).name
    except ValueError:
        raise ValueError(f"Invalid day number {day} for format {format_type}")


def convert_weekday_list(days: List[int], from_format: str, to_format: str) -> List[int]:
    """
    Convert a list of weekday numbers from one format to another.
    
    Args:
        days: List of day numbers in the source format
        from_format: Source format ("model", "python", or "sunday_first")
        to_format: Target format ("model", "python", or "sunday_first")
        
    Returns:
        List of day numbers in the target format
        
    Raises:
        ValueError: If format types are invalid or days are out of range
        
    Examples:
        >>> convert_weekday_list([1, 2, 3], "model", "python")
        [6, 0, 1]
        >>> convert_weekday_list([0, 1, 2], "python", "sunday_first")
        [1, 2, 3]
    """
    if from_format == to_format:
        return days.copy()
    
    # Define conversion functions based on format combinations
    conversion_map = {
        ("model", "python"): model_to_python_weekday,
        ("python", "model"): python_weekday_to_model,
        ("model", "sunday_first"): model_to_sunday_first,
        ("sunday_first", "model"): sunday_first_to_model,
        ("python", "sunday_first"): python_weekday_to_sunday_first,
        ("sunday_first", "python"): sunday_first_to_python_weekday,
    }
    
    key = (from_format, to_format)
    if key not in conversion_map:
        raise ValueError(f"Invalid format combination: from '{from_format}' to '{to_format}'")
    
    converter = conversion_map[key]
    return [converter(day) for day in days]


def weekday_from_date(date: datetime, format_type: str = "model") -> int:
    """
    Get the weekday number from a datetime object in the specified format.
    
    Args:
        date: datetime object
        format_type: Output format ("model", "python", or "sunday_first")
        
    Returns:
        Weekday number in the specified format
        
    Examples:
        >>> from datetime import date
        >>> weekday_from_date(date(2025, 7, 15), "model")  # Tuesday
        3
        >>> weekday_from_date(date(2025, 7, 15), "python")  # Tuesday
        1
        >>> weekday_from_date(date(2025, 7, 15), "sunday_first")  # Tuesday
        2
    """
    python_weekday = date.weekday()
    
    if format_type == "python":
        return python_weekday
    elif format_type == "model":
        return python_weekday_to_model(python_weekday)
    elif format_type == "sunday_first":
        return python_weekday_to_sunday_first(python_weekday)
    else:
        raise ValueError(f"Invalid format_type: {format_type}. Must be 'model', 'python', or 'sunday_first'.")


# Weekday names for reference
WEEKDAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

# Quick reference guide
CONVERSION_REFERENCE = """
Weekday Conversion Reference:
============================
Day        | Model | Python | Sunday-first
-----------|-------|--------|-------------
Sunday     |   1   |   6    |     0
Monday     |   2   |   0    |     1
Tuesday    |   3   |   1    |     2
Wednesday  |   4   |   2    |     3
Thursday   |   5   |   3    |     4
Friday     |   6   |   4    |     5
Saturday   |   7   |   5    |     6

Model format: Sunday=1 (used by upstream data)
Python format: Monday=0 (datetime.weekday())
Sunday-first: Sunday=0 (internal indexing)
"""


def print_conversion_reference():
    """Print the weekday conversion reference guide."""
    print(CONVERSION_REFERENCE)