"""
Pydantic data models for workforce analytics system.
Provides type safety and data validation for all data structures.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from config.constants import VarianceType, ControlMethod


class ModelHours(BaseModel):
    """Model hours data for a specific facility and role"""
    
    location_key: str = Field(description="Unique facility identifier")
    facility: str = Field(description="Facility name")
    role: str = Field(description="Staff role name")
    model_hours: float = Field(description="Expected hours for this role", ge=0)
    date: Optional[datetime] = Field(default=None, description="Date for the model data")
    role_sort: Optional[int] = Field(default=None, description="Role sorting order")
    cost_center_sort: Optional[int] = Field(default=None, description="Cost center sorting order")
    
    @validator('model_hours')
    def validate_model_hours(cls, v):
        if v < 0:
            raise ValueError('Model hours cannot be negative')
        return round(v, 2)


class FacilityHours(BaseModel):
    """Actual hours data for facility employees"""
    
    location_key: str = Field(description="Unique facility identifier")
    facility: str = Field(description="Facility name")
    role: str = Field(description="Staff role name")
    date: datetime = Field(description="Date of work")
    actual_hours: float = Field(description="Actual hours worked", ge=0)
    employee_id: Optional[str] = Field(default=None, description="Employee identifier")
    employee_name: Optional[str] = Field(default=None, description="Employee name")
    role_sort: Optional[int] = Field(default=None, description="Role sorting order")
    cost_center_sort: Optional[int] = Field(default=None, description="Cost center sorting order")
    week_start: Optional[datetime] = Field(default=None, description="Start of week for aggregation")
    
    @validator('actual_hours')
    def validate_actual_hours(cls, v):
        if v < 0:
            raise ValueError('Actual hours cannot be negative')
        return round(v, 2)


class StatisticalSummary(BaseModel):
    """Statistical summary for facility/role combination"""
    
    facility: str = Field(description="Facility name")
    role: str = Field(description="Staff role name")
    n_samples: int = Field(description="Number of data points", ge=0)
    mean: float = Field(description="Mean value")
    median: float = Field(description="Median value")
    std_dev: float = Field(description="Standard deviation", ge=0)
    mad: float = Field(description="Median Absolute Deviation", ge=0)
    control_method: ControlMethod = Field(description="Statistical control method used")
    upper_control_limit: float = Field(description="Upper control limit")
    lower_control_limit: float = Field(description="Lower control limit")
    is_normal_distribution: bool = Field(description="Whether data follows normal distribution")
    normality_p_value: Optional[float] = Field(default=None, description="P-value from normality test")
    
    @validator('lower_control_limit')
    def validate_lower_control_limit(cls, v):
        # Lower control limit cannot be negative for hours data
        return max(v, 0.0)


class VarianceResult(BaseModel):
    """Result of variance detection analysis"""
    
    facility: str = Field(description="Facility name")
    role: str = Field(description="Staff role name")
    date: datetime = Field(description="Date of variance")
    variance_type: VarianceType = Field(description="Type of variance detected")
    variance_value: float = Field(description="Magnitude of variance")
    variance_percentage: Optional[float] = Field(default=None, description="Variance as percentage")
    is_exception: bool = Field(description="Whether this is flagged as an exception")
    threshold_used: Optional[float] = Field(default=None, description="Threshold value used for detection")
    model_hours: Optional[float] = Field(default=None, description="Expected model hours")
    actual_hours: Optional[float] = Field(default=None, description="Actual hours worked")
    control_limit_violated: Optional[str] = Field(default=None, description="Which control limit was violated")
    
    @validator('variance_percentage')
    def validate_variance_percentage(cls, v):
        if v is not None:
            return round(v, 2)
        return v


class TrendAnalysisResult(BaseModel):
    """Result of trend analysis for facility/role combination"""
    
    facility: str = Field(description="Facility name")
    role: str = Field(description="Staff role name")
    analysis_start_date: datetime = Field(description="Start date of trend analysis")
    analysis_end_date: datetime = Field(description="End date of trend analysis")
    slope: float = Field(description="Linear regression slope")
    p_value: float = Field(description="Statistical significance p-value")
    r_squared: float = Field(description="R-squared value for fit quality")
    is_significant_trend: bool = Field(description="Whether trend is statistically significant")
    trend_direction: str = Field(description="Trend direction: increasing, decreasing, stable")
    weeks_analyzed: int = Field(description="Number of weeks included in analysis", ge=1)
    
    @validator('trend_direction')
    def validate_trend_direction(cls, v):
        valid_directions = ['increasing', 'decreasing', 'stable']
        if v not in valid_directions:
            raise ValueError(f'Trend direction must be one of: {valid_directions}')
        return v


class ExceptionSummary(BaseModel):
    """Summary of all exceptions for a facility"""
    
    facility: str = Field(description="Facility name")
    analysis_period_start: datetime = Field(description="Start of analysis period")
    analysis_period_end: datetime = Field(description="End of analysis period")
    total_exceptions: int = Field(description="Total number of exceptions", ge=0)
    model_variances: int = Field(description="Number of model variance exceptions", ge=0)
    statistical_exceptions: int = Field(description="Number of statistical exceptions", ge=0)
    trend_exceptions: int = Field(description="Number of trend exceptions", ge=0)
    roles_with_exceptions: List[str] = Field(description="List of roles with exceptions")
    severity_score: float = Field(description="Overall severity score", ge=0.0, le=100.0)
    
    @validator('severity_score')
    def validate_severity_score(cls, v):
        return round(v, 2)


class FacilityKPI(BaseModel):
    """Key Performance Indicators for a facility"""
    
    facility: str = Field(description="Facility name")
    total_model_hours: float = Field(description="Total expected model hours", ge=0)
    total_actual_hours: float = Field(description="Total actual hours worked", ge=0)
    variance_percentage: float = Field(description="Overall variance percentage")
    roles_analyzed: int = Field(description="Number of roles analyzed", ge=0)
    roles_with_exceptions: int = Field(description="Number of roles with exceptions", ge=0)
    exception_rate: float = Field(description="Percentage of roles with exceptions", ge=0.0, le=100.0)
    average_variance: float = Field(description="Average variance across all roles")
    largest_variance: float = Field(description="Largest individual variance")
    most_problematic_role: Optional[str] = Field(default=None, description="Role with most exceptions")
    
    @validator('exception_rate', 'variance_percentage', 'average_variance', 'largest_variance')
    def round_percentages(cls, v):
        return round(v, 2)


class ReportMetadata(BaseModel):
    """Metadata for generated reports"""
    
    facility: str = Field(description="Facility name")
    generated_at: datetime = Field(description="Report generation timestamp")
    analysis_period_start: datetime = Field(description="Start of analysis period")
    analysis_period_end: datetime = Field(description="End of analysis period")
    control_variables_used: Dict[str, Any] = Field(description="Control variables used in analysis")
    total_data_points: int = Field(description="Total data points analyzed", ge=0)
    has_exceptions: bool = Field(description="Whether facility has any exceptions")
    report_file_path: Optional[str] = Field(default=None, description="Path to generated report file")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ValidationError(BaseModel):
    """Data validation error details"""
    
    error_type: str = Field(description="Type of validation error")
    field_name: str = Field(description="Field that failed validation")
    error_message: str = Field(description="Detailed error message")
    invalid_value: Optional[Any] = Field(default=None, description="The invalid value")
    suggested_fix: Optional[str] = Field(default=None, description="Suggested fix for the error")


class DataQualityException(BaseModel):
    """Data quality issue captured during normalization instead of dropping rows"""
    
    row_index: int = Field(description="Original row index in the dataset")
    facility: Optional[str] = Field(default=None, description="Facility name if available")
    role: Optional[str] = Field(default=None, description="Role name if available")
    employee_id: Optional[str] = Field(default=None, description="Employee ID if available")
    issue_type: str = Field(description="Type of data quality issue")
    field_name: str = Field(description="Field that has the issue")
    original_value: Optional[str] = Field(default=None, description="Original problematic value")
    corrected_value: Optional[str] = Field(default=None, description="Corrected value if applicable")
    severity: str = Field(description="Severity level: low, medium, high, critical")
    description: str = Field(description="Human-readable description of the issue")
    suggested_action: str = Field(description="Recommended action to resolve the issue")
    processing_timestamp: datetime = Field(default_factory=datetime.now, description="When the issue was detected")
    
    @validator('severity')
    def validate_severity(cls, v):
        valid_severities = ['low', 'medium', 'high', 'critical']
        if v not in valid_severities:
            raise ValueError(f'Severity must be one of: {valid_severities}')
        return v
    
    @validator('issue_type')
    def validate_issue_type(cls, v):
        valid_types = [
            'invalid_date', 'negative_hours', 'missing_required_field',
            'invalid_hours_format', 'invalid_role_name', 'invalid_facility_name',
            'date_parsing_failed', 'hours_conversion_failed', 'empty_value'
        ]
        if v not in valid_types:
            raise ValueError(f'Issue type must be one of: {valid_types}')
        return v


class UnmappedHoursResult(BaseModel):
    """Result of unmapped hours analysis by category and employee"""
    
    facility: str = Field(description="Facility name")
    category: str = Field(description="Unmapped category (e.g., 'Unmapped Nursing')")
    employee_name: str = Field(description="Employee name")
    employee_id: str = Field(description="Employee identifier")
    total_hours: float = Field(description="Total hours worked in this category", ge=0)
    percentage_of_category: float = Field(description="Percentage of this category's total hours", ge=0.0, le=100.0)
    analysis_period_start: datetime = Field(description="Start of analysis period")
    analysis_period_end: datetime = Field(description="End of analysis period")
    
    @validator('total_hours', 'percentage_of_category')
    def round_values(cls, v):
        return round(v, 2)


class UnmappedCategorySummary(BaseModel):
    """Summary statistics for an unmapped category"""
    
    facility: str = Field(description="Facility name")
    category: str = Field(description="Unmapped category (e.g., 'Unmapped Nursing')")
    total_hours: float = Field(description="Total hours in this category", ge=0)
    employee_count: int = Field(description="Number of employees in this category", ge=0)
    percentage_of_total_unmapped: float = Field(description="Percentage of all unmapped hours", ge=0.0, le=100.0)
    average_hours_per_employee: float = Field(description="Average hours per employee", ge=0)
    analysis_period_start: datetime = Field(description="Start of analysis period")
    analysis_period_end: datetime = Field(description="End of analysis period")
    
    @validator('total_hours', 'percentage_of_total_unmapped', 'average_hours_per_employee')
    def round_values(cls, v):
        return round(v, 2)


class DataQualitySummary(BaseModel):
    """Summary of data quality issues for reporting"""
    
    total_records_processed: int = Field(description="Total number of records processed", ge=0)
    total_issues_found: int = Field(description="Total number of data quality issues", ge=0)
    issues_by_type: Dict[str, int] = Field(description="Count of issues by type")
    issues_by_severity: Dict[str, int] = Field(description="Count of issues by severity")
    facilities_affected: List[str] = Field(description="List of facilities with data quality issues")
    most_common_issue: Optional[str] = Field(default=None, description="Most frequently occurring issue type")
    data_quality_score: float = Field(description="Overall data quality score (0-100)", ge=0.0, le=100.0)
    
    @validator('data_quality_score')
    def round_quality_score(cls, v):
        return round(v, 2)


class OvertimeEmployee(BaseModel):
    """Employee overtime data for reporting"""
    
    employee_id: str = Field(description="Employee identifier")
    employee_name: str = Field(description="Employee name")
    total_overtime_hours: float = Field(description="Total overtime hours during period", ge=0)
    days_with_overtime: int = Field(description="Number of days with overtime", ge=0)
    average_daily_overtime: float = Field(description="Average daily overtime hours", ge=0)
    primary_role: str = Field(description="Most common role worked during period")
    rank: int = Field(description="Rank in top overtime list (1, 2, 3, etc.)", ge=1)
    
    @validator('total_overtime_hours', 'average_daily_overtime')
    def round_hours(cls, v):
        return round(v, 2)


class OvertimeFunctionGroup(BaseModel):
    """Overtime employees grouped by function (clinical/non-clinical)"""
    
    function: str = Field(description="Function type: clinical or non-clinical")
    display_name: str = Field(description="Display name for the function group")
    employees: List[OvertimeEmployee] = Field(description="Top employees in this function group")
    total_overtime_hours: float = Field(description="Total overtime hours for this function", ge=0)
    total_employees_in_function: int = Field(description="Total employees with overtime in this function", ge=0)
    
    @validator('total_overtime_hours')
    def round_group_hours(cls, v):
        return round(v, 2)


class OvertimeAnalysis(BaseModel):
    """Overtime analysis results for a facility"""
    
    facility: str = Field(description="Facility name")
    top_employees: List[OvertimeEmployee] = Field(description="Top N employees by overtime hours (legacy)")
    clinical_group: Optional[OvertimeFunctionGroup] = Field(default=None, description="Clinical employees group")
    non_clinical_group: Optional[OvertimeFunctionGroup] = Field(default=None, description="Non-clinical employees group")
    total_employees_with_overtime: int = Field(description="Total employees with any overtime", ge=0)
    top_count_requested: int = Field(description="Number of top employees requested", ge=1)
    total_overtime_hours_facility: float = Field(description="Total overtime hours for entire facility", ge=0)
    analysis_period_start: datetime = Field(description="Start of analysis period")
    analysis_period_end: datetime = Field(description="End of analysis period")
    
    @validator('total_overtime_hours_facility')
    def round_facility_hours(cls, v):
        return round(v, 2)


class VarianceEmployee(BaseModel):
    """Employee variance data for reporting (hours above model)"""
    
    employee_id: str = Field(description="Employee identifier")
    employee_name: str = Field(description="Employee name")
    total_variance_hours: float = Field(description="Total variance hours above model during period", ge=0)
    days_with_variance: int = Field(description="Number of days with variance above model", ge=0)
    average_daily_variance: float = Field(description="Average daily variance hours above model", ge=0)
    primary_role: str = Field(description="Most common role worked during period")
    rank: int = Field(description="Rank in top variance list (1, 2, 3, etc.)", ge=1)
    
    @validator('total_variance_hours', 'average_daily_variance')
    def round_hours(cls, v):
        return round(v, 2)


class VarianceFunctionGroup(BaseModel):
    """Variance employees grouped by function (clinical/non-clinical)"""
    
    function: str = Field(description="Function type: clinical or non-clinical")
    display_name: str = Field(description="Display name for the function group")
    employees: List[VarianceEmployee] = Field(description="Top employees in this function group")
    total_variance_hours: float = Field(description="Total variance hours for this function", ge=0)
    total_employees_in_function: int = Field(description="Total employees with variance in this function", ge=0)
    
    @validator('total_variance_hours')
    def round_group_hours(cls, v):
        return round(v, 2)


class VarianceEmployeesAnalysis(BaseModel):
    """Variance employees analysis results for a facility (hours above model)"""
    
    facility: str = Field(description="Facility name")
    top_employees: List[VarianceEmployee] = Field(description="Top N employees by variance hours (legacy)")
    clinical_group: Optional[VarianceFunctionGroup] = Field(default=None, description="Clinical employees group")
    non_clinical_group: Optional[VarianceFunctionGroup] = Field(default=None, description="Non-clinical employees group")
    total_employees_with_variance: int = Field(description="Total employees with any variance above model", ge=0)
    top_count_requested: int = Field(description="Number of top employees requested", ge=1)
    total_variance_hours_facility: float = Field(description="Total variance hours for entire facility", ge=0)
    analysis_period_start: datetime = Field(description="Start of analysis period")
    analysis_period_end: datetime = Field(description="End of analysis period")
    
    @validator('total_variance_hours_facility')
    def round_facility_hours(cls, v):
        return round(v, 2)


class UnmappedEmployee(BaseModel):
    """Employee unmapped hours data for reporting (per employee-role combination)"""
    
    employee_id: str = Field(description="Employee identifier")
    employee_name: str = Field(description="Employee name")
    role: str = Field(description="Role being worked by the employee")
    total_unmapped_hours: float = Field(description="Total unmapped hours during period for this role", ge=0)
    days_with_unmapped: int = Field(description="Number of days with unmapped hours for this role", ge=0)
    average_daily_unmapped: float = Field(description="Average daily unmapped hours for this role", ge=0)
    primary_category: str = Field(description="Most common unmapped category worked during period for this role")
    rank: int = Field(description="Rank in top unmapped list (1, 2, 3, etc.)", ge=1)
    
    @validator('total_unmapped_hours', 'average_daily_unmapped')
    def round_hours(cls, v):
        return round(v, 2)


class UnmappedFunctionGroup(BaseModel):
    """Unmapped hours employees grouped by function (clinical/non-clinical)"""
    
    function: str = Field(description="Function type: clinical or non-clinical")
    display_name: str = Field(description="Display name for the function group")
    employees: List[UnmappedEmployee] = Field(description="Top employees in this function group")
    total_unmapped_hours: float = Field(description="Total unmapped hours for this function", ge=0)
    total_employees_in_function: int = Field(description="Total employees with unmapped hours in this function", ge=0)
    
    @validator('total_unmapped_hours')
    def round_group_hours(cls, v):
        return round(v, 2)


class EmployeeOvertimeSummary(BaseModel):
    """Summary of overtime hours for a single employee"""
    
    employee_id: str = Field(description="Employee identifier")
    employee_name: str = Field(description="Employee name")
    total_hours: float = Field(description="Total hours worked across all roles", ge=0)
    overtime_hours: float = Field(description="Hours over the overtime threshold", ge=0)
    primary_role: str = Field(description="Role where employee worked most hours")
    
    @validator('total_hours', 'overtime_hours')
    def round_hours(cls, v):
        return round(v, 2)


class OvertimeResult(BaseModel):
    """Result of overtime analysis for a facility"""
    
    facility: str = Field(description="Facility name")
    total_overtime_hours: float = Field(description="Total overtime hours for the facility", ge=0)
    employee_count: int = Field(description="Number of employees with overtime", ge=0)
    top_overtime_employees: List[EmployeeOvertimeSummary] = Field(description="Top employees by overtime hours")
    
    @validator('total_overtime_hours')
    def round_hours(cls, v):
        return round(v, 2)


class TopUnmappedAnalysis(BaseModel):
    """Top unmapped hours analysis results for a facility"""
    
    facility: str = Field(description="Facility name")
    top_employees: List[UnmappedEmployee] = Field(description="Top N employees by unmapped hours (legacy)")
    clinical_group: Optional[UnmappedFunctionGroup] = Field(default=None, description="Clinical employees group")
    non_clinical_group: Optional[UnmappedFunctionGroup] = Field(default=None, description="Non-clinical employees group")
    total_employees_with_unmapped: int = Field(description="Total employees with any unmapped hours", ge=0)
    top_count_requested: int = Field(description="Number of top employees requested", ge=1)
    total_unmapped_hours_facility: float = Field(description="Total unmapped hours for entire facility", ge=0)
    analysis_period_start: datetime = Field(description="Start of analysis period")
    analysis_period_end: datetime = Field(description="End of analysis period")
    
    @validator('total_unmapped_hours_facility')
    def round_facility_hours(cls, v):
        return round(v, 2)