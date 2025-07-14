"""
Logging configuration (F-7) - Comprehensive logging setup for troubleshooting.
Implements structured logging with file and console handlers.
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from typing import Optional

from config.constants import LOG_FORMAT, LOG_DATE_FORMAT


def setup_logging(log_level: str = "INFO", 
                 log_dir: str = "logs",
                 log_file: str = "workforce_analytics.log",
                 max_file_size: int = 10 * 1024 * 1024,  # 10MB
                 backup_count: int = 5,
                 console_output: bool = True) -> logging.Logger:
    """
    Set up comprehensive logging configuration (F-7).
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files
        log_file: Name of the log file
        max_file_size: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
        console_output: Whether to output logs to console
        
    Returns:
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger("workforce_analytics")
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        fmt=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT
    )
    
    # File handler with rotation
    log_file_path = os.path.join(log_dir, log_file)
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_file_path,
        maxBytes=max_file_size,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)  # File gets all messages
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Console handler (if enabled)
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # Log startup message
    logger.info(f"Logging initialized - Level: {log_level}, File: {log_file_path}")
    
    return logger


def setup_module_logger(module_name: str, parent_logger: Optional[logging.Logger] = None) -> logging.Logger:
    """
    Set up a module-specific logger that inherits from parent logger.
    
    Args:
        module_name: Name of the module (e.g., "ingestion.model_loader")
        parent_logger: Parent logger to inherit from
        
    Returns:
        Module-specific logger
    """
    if parent_logger:
        logger_name = f"{parent_logger.name}.{module_name}"
    else:
        logger_name = f"workforce_analytics.{module_name}"
    
    return logging.getLogger(logger_name)


def log_function_entry(logger: logging.Logger, func_name: str, **kwargs) -> None:
    """
    Log function entry with parameters (for debugging).
    
    Args:
        logger: Logger instance
        func_name: Name of the function being called
        **kwargs: Function parameters to log
    """
    params = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
    logger.debug(f"ENTER {func_name}({params})")


def log_function_exit(logger: logging.Logger, func_name: str, result=None, duration: Optional[float] = None) -> None:
    """
    Log function exit with result and duration (for debugging).
    
    Args:
        logger: Logger instance
        func_name: Name of the function being exited
        result: Function result (optional)
        duration: Execution duration in seconds (optional)
    """
    msg_parts = [f"EXIT {func_name}"]
    
    if result is not None:
        if hasattr(result, '__len__') and not isinstance(result, str):
            msg_parts.append(f"result_count={len(result)}")
        else:
            msg_parts.append(f"result_type={type(result).__name__}")
    
    if duration is not None:
        msg_parts.append(f"duration={duration:.3f}s")
    
    logger.debug(" - ".join(msg_parts))


def log_dataframe_info(logger: logging.Logger, df, df_name: str = "DataFrame") -> None:
    """
    Log information about a DataFrame for debugging.
    
    Args:
        logger: Logger instance
        df: Pandas DataFrame
        df_name: Name/description of the DataFrame
    """
    if df is None:
        logger.debug(f"{df_name}: None")
        return
    
    if hasattr(df, 'empty') and df.empty:
        logger.debug(f"{df_name}: Empty DataFrame")
        return
    
    try:
        shape_info = f"shape={df.shape}"
        columns_info = f"columns={list(df.columns)}"
        memory_usage = f"memory={df.memory_usage(deep=True).sum() / 1024:.1f}KB"
        
        logger.debug(f"{df_name}: {shape_info}, {columns_info}, {memory_usage}")
        
        # Log data types and null counts for key columns
        if hasattr(df, 'dtypes'):
            dtype_info = []
            for col in df.columns:
                null_count = df[col].isnull().sum()
                dtype_info.append(f"{col}({df[col].dtype.name}, {null_count} nulls)")
            
            if len(dtype_info) <= 10:  # Only log if reasonable number of columns
                logger.debug(f"{df_name} details: {', '.join(dtype_info)}")
    
    except Exception as e:
        logger.debug(f"Error logging DataFrame info for {df_name}: {str(e)}")


def log_performance_metrics(logger: logging.Logger, operation: str, 
                          records_processed: int, duration: float) -> None:
    """
    Log performance metrics for operations.
    
    Args:
        logger: Logger instance
        operation: Description of the operation
        records_processed: Number of records processed
        duration: Duration in seconds
    """
    if duration > 0:
        rate = records_processed / duration
        logger.info(f"PERFORMANCE {operation}: {records_processed} records in {duration:.2f}s "
                   f"({rate:.1f} records/sec)")
    else:
        logger.info(f"PERFORMANCE {operation}: {records_processed} records in <0.01s")


def log_memory_usage(logger: logging.Logger, operation: str) -> None:
    """
    Log current memory usage (if psutil is available).
    
    Args:
        logger: Logger instance
        operation: Description of the current operation
    """
    try:
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        logger.debug(f"MEMORY {operation}: {memory_mb:.1f} MB RSS")
    except ImportError:
        # psutil not available, skip memory logging
        pass
    except Exception as e:
        logger.debug(f"Error logging memory usage: {str(e)}")


def configure_third_party_loggers(level: str = "WARNING") -> None:
    """
    Configure logging levels for third-party libraries to reduce noise.
    
    Args:
        level: Logging level to set for third-party libraries
    """
    third_party_loggers = [
        'urllib3',
        'requests', 
        'matplotlib',
        'pandas',
        'numpy',
        'playwright'
    ]
    
    for logger_name in third_party_loggers:
        logging.getLogger(logger_name).setLevel(getattr(logging, level.upper()))


class ContextFilter(logging.Filter):
    """
    Custom filter to add context information to log records.
    """
    
    def __init__(self, facility: str = None, role: str = None):
        super().__init__()
        self.facility = facility
        self.role = role
    
    def filter(self, record):
        """Add context information to log record."""
        record.facility = getattr(record, 'facility', self.facility or 'N/A')
        record.role = getattr(record, 'role', self.role or 'N/A')
        return True


class TimedOperation:
    """
    Context manager for timing operations and logging performance.
    """
    
    def __init__(self, logger: logging.Logger, operation_name: str, 
                 log_entry: bool = True, log_exit: bool = True):
        self.logger = logger
        self.operation_name = operation_name
        self.log_entry = log_entry
        self.log_exit = log_exit
        self.start_time = None
        self.duration = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        if self.log_entry:
            self.logger.info(f"Starting {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = datetime.now()
        self.duration = (end_time - self.start_time).total_seconds()
        
        if exc_type is not None:
            self.logger.error(f"Failed {self.operation_name} after {self.duration:.2f}s: {exc_val}")
        elif self.log_exit:
            self.logger.info(f"Completed {self.operation_name} in {self.duration:.2f}s")


def create_session_logger(session_id: str, log_dir: str = "logs") -> logging.Logger:
    """
    Create a session-specific logger for tracking individual analysis runs.
    
    Args:
        session_id: Unique identifier for this analysis session
        log_dir: Directory for log files
        
    Returns:
        Session-specific logger
    """
    session_log_file = f"session_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    session_log_path = os.path.join(log_dir, session_log_file)
    
    # Create session logger
    session_logger = logging.getLogger(f"workforce_analytics.session.{session_id}")
    session_logger.setLevel(logging.DEBUG)
    
    # Create session file handler
    session_handler = logging.FileHandler(session_log_path, encoding='utf-8')
    session_handler.setLevel(logging.DEBUG)
    
    # Create detailed formatter for session logs
    session_formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(facility)s - %(role)s - %(message)s",
        datefmt=LOG_DATE_FORMAT
    )
    session_handler.setFormatter(session_formatter)
    
    # Add context filter
    session_handler.addFilter(ContextFilter())
    
    session_logger.addHandler(session_handler)
    
    session_logger.info(f"Session {session_id} started - Log file: {session_log_path}")
    
    return session_logger