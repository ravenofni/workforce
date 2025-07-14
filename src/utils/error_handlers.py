"""
Error handling utilities (F-8) - Custom exceptions and graceful error handling.
Provides comprehensive error handling throughout the application.
"""

import sys
import traceback
import functools
import logging
from typing import Any, Callable, Optional, Dict, Type
from enum import Enum


class ExitCode(Enum):
    """Exit codes for the application"""
    SUCCESS = 0
    GENERAL_ERROR = 1
    DATA_ERROR = 2
    CONFIG_ERROR = 3
    FILE_NOT_FOUND = 4
    VALIDATION_ERROR = 5
    STATISTICAL_ERROR = 6
    PDF_GENERATION_ERROR = 7
    MEMORY_ERROR = 8
    TIMEOUT_ERROR = 9


class WorkforceAnalyticsError(Exception):
    """Base exception class for workforce analytics application"""
    
    def __init__(self, message: str, exit_code: ExitCode = ExitCode.GENERAL_ERROR, 
                 details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.exit_code = exit_code
        self.details = details or {}
    
    def __str__(self):
        base_msg = super().__str__()
        if self.details:
            details_str = ", ".join([f"{k}={v}" for k, v in self.details.items()])
            return f"{base_msg} (Details: {details_str})"
        return base_msg


class DataIngestionError(WorkforceAnalyticsError):
    """Exception raised during data ingestion operations"""
    
    def __init__(self, message: str, file_path: Optional[str] = None, 
                 line_number: Optional[int] = None, **kwargs):
        details = kwargs
        if file_path:
            details['file_path'] = file_path
        if line_number:
            details['line_number'] = line_number
        
        super().__init__(message, ExitCode.DATA_ERROR, details)


class DataValidationError(WorkforceAnalyticsError):
    """Exception raised during data validation"""
    
    def __init__(self, message: str, invalid_records: Optional[int] = None, 
                 validation_rule: Optional[str] = None, **kwargs):
        details = kwargs
        if invalid_records:
            details['invalid_records'] = invalid_records
        if validation_rule:
            details['validation_rule'] = validation_rule
        
        super().__init__(message, ExitCode.VALIDATION_ERROR, details)


class StatisticalAnalysisError(WorkforceAnalyticsError):
    """Exception raised during statistical analysis"""
    
    def __init__(self, message: str, facility: Optional[str] = None, 
                 role: Optional[str] = None, **kwargs):
        details = kwargs
        if facility:
            details['facility'] = facility
        if role:
            details['role'] = role
        
        super().__init__(message, ExitCode.STATISTICAL_ERROR, details)


class ReportGenerationError(WorkforceAnalyticsError):
    """Exception raised during report generation"""
    
    def __init__(self, message: str, report_type: Optional[str] = None, 
                 facility: Optional[str] = None, **kwargs):
        details = kwargs
        if report_type:
            details['report_type'] = report_type
        if facility:
            details['facility'] = facility
        
        super().__init__(message, ExitCode.PDF_GENERATION_ERROR, details)


class ConfigurationError(WorkforceAnalyticsError):
    """Exception raised for configuration-related errors"""
    
    def __init__(self, message: str, config_key: Optional[str] = None, 
                 config_value: Optional[Any] = None, **kwargs):
        details = kwargs
        if config_key:
            details['config_key'] = config_key
        if config_value:
            details['config_value'] = config_value
        
        super().__init__(message, ExitCode.CONFIG_ERROR, details)


def handle_exceptions(exit_on_error: bool = True, 
                     log_traceback: bool = True,
                     default_exit_code: ExitCode = ExitCode.GENERAL_ERROR):
    """
    Decorator for comprehensive exception handling.
    
    Args:
        exit_on_error: Whether to exit the application on unhandled exceptions
        log_traceback: Whether to log the full traceback
        default_exit_code: Default exit code for unhandled exceptions
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger("workforce_analytics.error_handler")
            
            try:
                return func(*args, **kwargs)
                
            except WorkforceAnalyticsError as e:
                # Handle known application errors
                logger.error(f"Application error in {func.__name__}: {str(e)}")
                
                if log_traceback:
                    logger.debug(f"Traceback for {func.__name__}:", exc_info=True)
                
                if exit_on_error:
                    logger.critical(f"Exiting with code {e.exit_code.value}")
                    sys.exit(e.exit_code.value)
                else:
                    raise
                    
            except FileNotFoundError as e:
                # Handle file not found errors
                error_msg = f"File not found in {func.__name__}: {str(e)}"
                logger.error(error_msg)
                
                if log_traceback:
                    logger.debug(f"Traceback for {func.__name__}:", exc_info=True)
                
                if exit_on_error:
                    logger.critical(f"Exiting with code {ExitCode.FILE_NOT_FOUND.value}")
                    sys.exit(ExitCode.FILE_NOT_FOUND.value)
                else:
                    raise WorkforceAnalyticsError(error_msg, ExitCode.FILE_NOT_FOUND)
                    
            except MemoryError as e:
                # Handle memory errors
                error_msg = f"Memory error in {func.__name__}: {str(e)}"
                logger.error(error_msg)
                logger.error("Consider processing data in smaller chunks or increasing available memory")
                
                if exit_on_error:
                    logger.critical(f"Exiting with code {ExitCode.MEMORY_ERROR.value}")
                    sys.exit(ExitCode.MEMORY_ERROR.value)
                else:
                    raise WorkforceAnalyticsError(error_msg, ExitCode.MEMORY_ERROR)
                    
            except KeyboardInterrupt:
                # Handle user interruption
                logger.info("Operation interrupted by user")
                if exit_on_error:
                    sys.exit(130)  # Standard exit code for SIGINT
                else:
                    raise
                    
            except Exception as e:
                # Handle unexpected errors
                error_msg = f"Unexpected error in {func.__name__}: {str(e)}"
                logger.error(error_msg)
                
                if log_traceback:
                    logger.error(f"Full traceback for {func.__name__}:", exc_info=True)
                
                if exit_on_error:
                    logger.critical(f"Exiting with code {default_exit_code.value}")
                    sys.exit(default_exit_code.value)
                else:
                    raise WorkforceAnalyticsError(error_msg, default_exit_code)
        
        return wrapper
    return decorator


def safe_execute(operation: Callable, operation_name: str, 
                logger: logging.Logger, *args, **kwargs) -> tuple[bool, Any]:
    """
    Safely execute an operation and return success status with result.
    
    Args:
        operation: Function to execute
        operation_name: Name of the operation for logging
        logger: Logger instance
        *args: Arguments for the operation
        **kwargs: Keyword arguments for the operation
        
    Returns:
        Tuple of (success: bool, result: Any)
    """
    try:
        logger.debug(f"Starting safe execution of {operation_name}")
        result = operation(*args, **kwargs)
        logger.debug(f"Successfully completed {operation_name}")
        return True, result
        
    except WorkforceAnalyticsError as e:
        logger.error(f"Known error in {operation_name}: {str(e)}")
        return False, e
        
    except Exception as e:
        logger.error(f"Unexpected error in {operation_name}: {str(e)}")
        logger.debug(f"Traceback for {operation_name}:", exc_info=True)
        wrapped_error = WorkforceAnalyticsError(
            f"Unexpected error in {operation_name}: {str(e)}"
        )
        return False, wrapped_error


def validate_and_raise(condition: bool, error_class: Type[WorkforceAnalyticsError], 
                      message: str, **error_kwargs) -> None:
    """
    Validate a condition and raise an exception if it fails.
    
    Args:
        condition: Condition to validate (should be True for success)
        error_class: Exception class to raise if condition fails
        message: Error message
        **error_kwargs: Additional arguments for the exception
    """
    if not condition:
        raise error_class(message, **error_kwargs)


def create_error_summary(errors: list) -> Dict[str, Any]:
    """
    Create a summary of multiple errors for reporting.
    
    Args:
        errors: List of error objects or strings
        
    Returns:
        Dictionary with error summary statistics
    """
    summary = {
        'total_errors': len(errors),
        'error_types': {},
        'critical_errors': 0,
        'warnings': 0,
        'details': []
    }
    
    for error in errors:
        if isinstance(error, WorkforceAnalyticsError):
            error_type = type(error).__name__
            summary['error_types'][error_type] = summary['error_types'].get(error_type, 0) + 1
            
            if error.exit_code in [ExitCode.MEMORY_ERROR, ExitCode.DATA_ERROR]:
                summary['critical_errors'] += 1
            else:
                summary['warnings'] += 1
                
            summary['details'].append({
                'type': error_type,
                'message': str(error),
                'exit_code': error.exit_code.value,
                'details': error.details
            })
        else:
            # Handle string errors or other types
            summary['error_types']['Unknown'] = summary['error_types'].get('Unknown', 0) + 1
            summary['warnings'] += 1
            summary['details'].append({
                'type': 'Unknown',
                'message': str(error),
                'exit_code': ExitCode.GENERAL_ERROR.value,
                'details': {}
            })
    
    return summary


def log_error_summary(errors: list, logger: logging.Logger) -> None:
    """
    Log a summary of multiple errors.
    
    Args:
        errors: List of error objects
        logger: Logger instance
    """
    if not errors:
        logger.info("No errors to summarize")
        return
    
    summary = create_error_summary(errors)
    
    logger.error(f"Error Summary: {summary['total_errors']} total errors")
    logger.error(f"  Critical: {summary['critical_errors']}, Warnings: {summary['warnings']}")
    
    for error_type, count in summary['error_types'].items():
        logger.error(f"  {error_type}: {count}")
    
    # Log details for critical errors
    for detail in summary['details']:
        if detail['exit_code'] in [ExitCode.MEMORY_ERROR.value, ExitCode.DATA_ERROR.value]:
            logger.error(f"CRITICAL: {detail['message']}")


class ErrorCollector:
    """
    Utility class for collecting and managing errors during batch operations.
    """
    
    def __init__(self, max_errors: int = 100):
        self.errors = []
        self.max_errors = max_errors
        self.logger = logging.getLogger("workforce_analytics.error_collector")
    
    def add_error(self, error: Exception, context: Optional[str] = None) -> None:
        """Add an error to the collection."""
        if len(self.errors) >= self.max_errors:
            self.logger.warning(f"Maximum error count ({self.max_errors}) reached, ignoring additional errors")
            return
        
        error_record = {
            'error': error,
            'context': context,
            'timestamp': logging.Formatter().formatTime(logging.LogRecord(
                '', 0, '', 0, '', (), None
            ))
        }
        
        self.errors.append(error_record)
        
        if context:
            self.logger.error(f"Error in {context}: {str(error)}")
        else:
            self.logger.error(f"Error: {str(error)}")
    
    def has_errors(self) -> bool:
        """Check if any errors have been collected."""
        return len(self.errors) > 0
    
    def has_critical_errors(self) -> bool:
        """Check if any critical errors have been collected."""
        return any(
            isinstance(record['error'], WorkforceAnalyticsError) and
            record['error'].exit_code in [ExitCode.MEMORY_ERROR, ExitCode.DATA_ERROR]
            for record in self.errors
        )
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of collected errors."""
        return create_error_summary([record['error'] for record in self.errors])
    
    def log_summary(self) -> None:
        """Log summary of all collected errors."""
        if not self.has_errors():
            self.logger.info("No errors collected")
            return
        
        log_error_summary([record['error'] for record in self.errors], self.logger)
    
    def clear(self) -> None:
        """Clear all collected errors."""
        self.errors.clear()
        self.logger.debug("Error collection cleared")