# Workforce Analytics System - Technical Planning & Architecture

## 🏗️ System Architecture

### Core Design Principles
- **Modularity**: Clear separation of concerns across ingestion, analysis, and reporting
- **Type Safety**: Comprehensive Pydantic models for data validation
- **Error Resilience**: Robust error handling with graceful degradation
- **Memory Efficiency**: Pandas-based operations optimized for large datasets
- **Configurability**: Environment-based settings with CLI overrides

### Project Structure

```
workforce/
├── main.py                          # CLI entry point with complete pipeline orchestration
├── config/                          # Configuration management layer
│   ├── settings.py                  # Pydantic-based settings with environment integration
│   └── constants.py                 # Column mappings, constants, and enumerations
├── src/                            # Core application modules
│   ├── models/
│   │   └── data_models.py          # Pydantic models for type safety and validation
│   ├── ingestion/                  # Data loading and normalization (F-1, F-2)
│   │   ├── model_loader.py         # Model hours data loading with display (F-1a)
│   │   ├── hours_loader.py         # Facility hours with multi-format date parsing
│   │   └── normalizer.py           # Data standardization with flexible options
│   ├── analysis/                   # Statistical analysis engine (F-3, F-4)
│   │   ├── statistics.py           # Descriptive stats and control limits
│   │   ├── variance.py             # Multi-type variance detection
│   │   └── trends.py              # Linear regression trend analysis
│   ├── reporting/                  # Report generation pipeline (F-5, F-6)
│   │   ├── exceptions.py           # Exception compilation and structuring
│   │   ├── chart_generator.py      # Matplotlib/Seaborn chart generation
│   │   ├── pdf_generator.py        # Playwright-based PDF generation
│   │   ├── report_orchestrator.py  # Async report coordination
│   │   └── templates/              # Jinja2 HTML templates
│   └── utils/                      # Cross-cutting concerns (F-7, F-8)
│       ├── logging_config.py       # Structured logging with timing
│       └── error_handlers.py       # Exception handling and exit codes
├── examples/                       # Sample data and reference patterns
├── tests/                          # Unit test framework (pytest-based)
└── output/                         # Generated reports and analysis files
```

## 🔧 Technical Implementation Details

### Data Processing Pipeline

#### 1. Data Ingestion Layer
- **Model Data (F-1)**: 
  - Loads CSV with workforce model expectations
  - **Date Handling**: Preserves dates as strings (only DayOfWeek matters)
  - **Validation**: Required columns check, ModelHours numeric conversion
  - **Display**: F-1a formatted table with day-specific breakdowns

- **Facility Data (F-2)**:
  - Loads actual hours worked with multi-facility support
  - **Date Parsing**: Flexible parsing (M/D/YY ↔ M/D/YYYY) with automatic fallback
  - **Weekly Aggregation**: Sunday-Saturday weekly summaries
  - **Validation**: ActualHours validation, negative hours handling

#### 2. Normalization Layer (F-2)
- **Date Standardization**: MMDDYYYY format with error handling
- **Hours Conversion**: Float conversion with rounding to 2 decimals
- **Role Harmonization**: Regex-based role name standardization
- **Facility Normalization**: Case and whitespace consistency

#### 3. Statistical Analysis Engine

##### Variance Detection (F-3a, F-3b)
- **Model Variance**: Percentage deviation from expected hours
- **Statistical Control**: Upper/lower control limit violations
- **Control Method Selection**: 
  - Normal distribution → Mean ± 3σ
  - Non-normal distribution → Median ± 3×MAD
- **Normality Testing**: Shapiro-Wilk with sample size limitations

##### Trend Analysis (F-4)
- **Linear Regression**: scipy.stats.linregress for trend detection
- **Significance Testing**: P-value thresholds for trend validation
- **Temporal Grouping**: Role × Day × Facility combinations
- **Direction Detection**: Increasing/decreasing trend classification

#### 4. Report Generation Pipeline (F-5, F-6)

##### Exception Compilation (F-5)
- **Structured Assembly**: Variance + Trend results consolidation
- **Severity Classification**: Exception type and magnitude scoring
- **Facility Grouping**: Per-facility exception aggregation

##### PDF Generation (F-6)
- **Template Engine**: Jinja2 HTML templates with professional styling
- **Chart Generation**: Matplotlib/Seaborn for statistical visualizations
- **PDF Conversion**: Playwright browser automation for high-quality PDFs
- **Async Processing**: Concurrent report generation for multiple facilities

### Configuration Management

#### Environment-based Settings
- **Priority Order**: CLI args > Environment variables > Defaults
- **Validation**: Pydantic models with type checking and constraints
- **Directory Management**: Automatic creation of output/reports/logs directories

#### Control Variables (F-0)
```python
class ControlVariables(BaseModel):
    days_to_drop: int = 7                    # F-0a: Historical data trimming
    days_to_process: int = 84                # F-0b: Analysis window
    new_data_day: int = 1                    # F-0c: Clean data day (Monday)
    use_data_day: bool = True                # F-0d: Use day vs drop days
    use_statistics: bool = True              # F-0e: Enable statistical analysis
    variance_threshold: float = 15.0         # F-0f: Model variance threshold
    weeks_for_control: int = 12              # F-0g: Control limit calculation
    weeks_for_trends: int = 8                # F-0h: Trend analysis window
```

### Error Handling Strategy (F-8)

#### Exception Hierarchy
- **WorkforceAnalyticsError**: Base exception with context
- **Exit Codes**: Structured exit codes for automation integration
- **Error Recovery**: Graceful degradation when components fail

#### Logging Architecture (F-7)
- **Structured Logging**: Context-aware logging with facility/role identifiers
- **Performance Timing**: TimedOperation context manager for benchmarking
- **Log Rotation**: Automatic log file management with size limits
- **Multi-destination**: Console + file logging with level separation

## 🎯 Design Decisions & Rationale

### Technology Stack Choices

#### Core Libraries
- **pandas**: DataFrame operations for statistical analysis and data manipulation
- **scipy**: Statistical functions (Shapiro-Wilk, linear regression)
- **Pydantic**: Type safety and configuration validation
- **python-dotenv**: Environment variable management

#### PDF Generation Stack
- **Playwright**: Modern browser automation (replaces deprecated pyppeteer)
- **Jinja2**: Template engine for maintainable HTML generation
- **matplotlib/seaborn**: Professional statistical chart generation

### Date Handling Strategy
- **Problem**: Multiple date formats (M/D/YY vs M/D/YYYY) in source data
- **Solution**: Flexible parsing with automatic fallback to pandas automatic parsing
- **Model Data**: Skip date parsing entirely (only DayOfWeek matters for modeling)
- **Facility Data**: Parse dates for temporal analysis and weekly aggregation

### Memory Management
- **Chunked Processing**: Process facilities individually to manage memory
- **Efficient DataFrames**: Avoid unnecessary copying, use views where possible
- **Chart Memory**: Generate charts individually and cleanup after PDF inclusion

### Statistical Method Selection
- **Normality Testing**: Automatic selection of appropriate control methods
- **Sample Size Handling**: Truncate samples >5000 for scipy.stats limitations
- **Robustness**: MAD-based methods for non-normal distributions

## 🔄 Data Flow Architecture

### Pipeline Stages
1. **Ingestion**: CSV → Raw DataFrames with validation
2. **Normalization**: Raw → Standardized data with type conversion
3. **Aggregation**: Daily → Weekly summaries for trend analysis
4. **Statistical Analysis**: Weekly data → Control limits + variance detection
5. **Trend Analysis**: Time series → Linear regression results
6. **Exception Compilation**: Analysis results → Structured exception reports
7. **Report Generation**: Exceptions → Professional PDF reports

### Data Models & Validation

#### Pydantic Models
```python
class FacilityHours(BaseModel):
    facility: str
    role: str
    actual_hours: float
    date: datetime
    week_start: datetime

class ModelHours(BaseModel):
    facility: str
    role: str  
    model_hours: float
    day_of_week: str

class StatisticalSummary(BaseModel):
    facility: str
    role: str
    control_method: ControlMethod
    mean_hours: float
    control_limits: Tuple[float, float]
```

## 🚀 Performance & Scalability

### Optimization Strategies
- **Vectorized Operations**: Pandas/numpy vectorization for statistical calculations
- **Memory-efficient Grouping**: Process facility-role combinations individually
- **Async Report Generation**: Concurrent PDF generation for multiple facilities
- **Caching**: Reuse statistical calculations across variance detection

### Scalability Considerations
- **Large Dataset Handling**: Memory-efficient pandas operations
- **Multi-facility Support**: Parallel processing capability design
- **Storage Management**: Automatic cleanup of temporary files and logs

## 🔒 Data Integrity & Validation

### Input Validation
- **Required Columns**: Strict validation of CSV column presence
- **Data Types**: Automatic conversion with error handling
- **Range Validation**: Negative hours detection and correction
- **Date Validation**: Multiple format support with fallback parsing

### Output Validation
- **Report Completeness**: Verify all expected sections are generated
- **Chart Generation**: Error handling for visualization failures
- **PDF Quality**: File size and formatting validation

## 📈 Future Architecture Considerations

### Extensibility Points
- **New Analysis Methods**: Plugin architecture for additional statistical tests
- **Data Source Integration**: Database connectivity for real-time data
- **Interactive Dashboards**: Web interface for dynamic analysis
- **API Endpoints**: REST API for programmatic access

### Performance Enhancements
- **Database Backend**: Migrate from CSV to database for large datasets
- **Distributed Processing**: Multi-process analysis for large facility counts
- **Incremental Analysis**: Delta processing for real-time updates

## 🧪 Testing Strategy

### Unit Testing Framework
- **pytest**: Comprehensive unit test coverage
- **Fixtures**: Reusable test data and mock configurations
- **Coverage Goals**: >90% code coverage for core analysis functions

### Integration Testing
- **End-to-end Pipeline**: Complete analysis workflow testing
- **Data Format Validation**: Multiple CSV format compatibility testing
- **Report Generation**: PDF output quality and completeness testing

This architecture provides a robust, scalable foundation for workforce analytics while maintaining code quality, performance, and maintainability standards.