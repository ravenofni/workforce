"""
Constants and column mappings for workforce analytics system.
Mirrors patterns from examples/data_processing.py lines 36-51.
"""

from enum import Enum
from typing import List


class FileColumns:
    """Column name constants for CSV files"""
    
    # Model data columns (from SampleModelData.csv)
    MODEL_LOCATION_KEY = "LOCATION_KEY"
    MODEL_LOCATION_NAME = "LOCATION_NAME"
    MODEL_HOURS_DATE = "HOURS_DATE"
    MODEL_DAY_OF_WEEK = "DAY_OF_WEEK"
    MODEL_DAY_NUMBER = "DAY_NUMBER"
    MODEL_TOTAL_HOURS = "TOTAL_HOURS"
    MODEL_STAFF_ROLE_NAME = "STAFF_ROLE_NAME"
    MODEL_WORKFORCE_MODEL_ROLE_SORT = "WORKFORCE_MODEL_ROLE_SORT"
    MODEL_COST_CENTER_SORT = "COST_CENTER_SORT"
    
    # Facility data columns (from SampleFacilityData.csv)
    FACILITY_LOCATION_KEY = "LOCATION_KEY"
    FACILITY_LOCATION_NAME = "LOCATION_NAME"
    FACILITY_HOURS_DATE = "HOURS_DATE"
    FACILITY_DAY_OF_WEEK = "DAY_OF_WEEK"
    FACILITY_DAY_NUMBER = "DAY_NUMBER"
    FACILITY_EMPLOYEE_ID = "EMPLOYEE_ID"
    FACILITY_EMPLOYEE_NAME = "EMPLOYEE_NAME"
    FACILITY_TOTAL_HOURS = "TOTAL_HOURS"
    FACILITY_STAFF_ROLE_NAME = "STAFF_ROLE_NAME"
    FACILITY_WORKFORCE_MODEL_ROLE_SORT = "WORKFORCE_MODEL_ROLE_SORT"
    FACILITY_COST_CENTER_SORT = "COST_CENTER_SORT"




class VarianceType(str, Enum):
    """Types of variance detection as specified in F-3"""
    MODEL = "model"          # Variance from model hours (F-0f)
    STATISTICAL = "statistical"  # Statistical abnormality (F-3a, F-3b)
    TREND = "trend"          # Trend analysis variance (F-4)


class ControlMethod(str, Enum):
    """Statistical control methods based on normality testing"""
    NORMAL = "normal"        # Standard deviation method for normal distributions
    MAD = "mad"             # Median Absolute Deviation for non-normal distributions


class DayOfWeek(int, Enum):
    """Day of week enumeration for F-0c"""
    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6
    SUNDAY = 7


# File path patterns - default paths for debug mode
DEFAULT_MODEL_FILE = "SampleModelData.csv"
DEFAULT_FACILITY_FILE = "SampleFacilityData.csv"
DEFAULT_FACILITY_DATA_PATH = "examples/SampleFacilityData.csv"
DEFAULT_MODEL_DATA_PATH = "examples/SampleModelData.csv"

# Statistical constants
NORMALITY_P_VALUE_THRESHOLD = 0.05  # P-value threshold for normality testing
CONTROL_LIMIT_MULTIPLIER = 3        # Standard deviations for control limits
MIN_SAMPLE_SIZE_NORMALITY = 3       # Minimum sample size for normality testing
MAX_SAMPLE_SIZE_NORMALITY = 5000    # Maximum sample size for scipy.stats.shapiro

# Report generation constants
PDF_MARGIN_INCHES = 1.0
PDF_FORMAT = "A4"
DATE_FORMAT = "%m/%d/%Y"            # MMDDYYYY format as specified in F-2
DATETIME_FORMAT = "%m/%d/%Y %H:%M:%S"

# Logging constants
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Exception criteria constants
DEFAULT_VARIANCE_THRESHOLD = 15.0   # Default percentage variance threshold
DEFAULT_WEEKS_FOR_CONTROL = 12     # Default weeks for control limit calculation
DEFAULT_WEEKS_FOR_TRENDS = 8       # Default weeks for trend analysis

# Required columns for validation
MODEL_REQUIRED_COLUMNS: List[str] = [
    FileColumns.MODEL_LOCATION_KEY,
    FileColumns.MODEL_LOCATION_NAME,
    FileColumns.MODEL_STAFF_ROLE_NAME,
    FileColumns.MODEL_TOTAL_HOURS,
    FileColumns.MODEL_HOURS_DATE
]

FACILITY_REQUIRED_COLUMNS: List[str] = [
    FileColumns.FACILITY_LOCATION_KEY,
    FileColumns.FACILITY_LOCATION_NAME,
    FileColumns.FACILITY_STAFF_ROLE_NAME,
    FileColumns.FACILITY_TOTAL_HOURS,
    FileColumns.FACILITY_HOURS_DATE
]