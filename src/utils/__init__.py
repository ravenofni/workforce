"""
Utility modules for workforce analytics.

This package contains cross-cutting utility modules that provide common functionality
across different components of the workforce analytics system.
"""

from .date_calculator import calculate_analysis_date_range, validate_date_range
from .weekday_converter import (
    model_to_python_weekday,
    python_weekday_to_model,
    model_to_sunday_first,
    sunday_first_to_model,
    python_weekday_to_sunday_first,
    sunday_first_to_python_weekday,
    get_weekday_name,
    convert_weekday_list,
    weekday_from_date,
    print_conversion_reference,
)
from .error_handlers import WorkforceAnalyticsError
from .logging_config import setup_logging, TimedOperation

__all__ = [
    # Date calculation
    "calculate_analysis_date_range",
    "validate_date_range",
    # Weekday conversion
    "model_to_python_weekday",
    "python_weekday_to_model",
    "model_to_sunday_first",
    "sunday_first_to_model",
    "python_weekday_to_sunday_first",
    "sunday_first_to_python_weekday",
    "get_weekday_name",
    "convert_weekday_list",
    "weekday_from_date",
    "print_conversion_reference",
    # Error handling
    "WorkforceAnalyticsError",
    # Logging
    "setup_logging",
    "TimedOperation",
]