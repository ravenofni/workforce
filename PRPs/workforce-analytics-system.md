name: "Workforce Analytics System - Comprehensive Implementation PRP"
description: "A comprehensive requirements document for the Workforce Resource Tool being developed."

## Purpose
Complete implementation of a workforce analytics system that ingests model vs actual hours data, performs statistical variance detection, generates reports, and produces facility-specific PDF reports with exceptions and trends.

## Core Principles
1. **Context is King**: Leverage existing examples and statistical patterns from the codebase
2. **Validation Loops**: Comprehensive testing with real data samples
3. **Information Dense**: Use established statistical and visualization patterns
4. **Progressive Success**: Build modular components that integrate seamlessly
5. **Global rules**: Follow all rules in CLAUDE.md and use base virtual environment

---

## Goal
Build a complete workforce analytics system that ingests workforce model hours vs actual hours, detects statistical variances using control limits and trend analysis, and generates per-facility PDF reports highlighting exceptions only. The system should support both batch processing (Phase 1) and future real-time capabilities (Phase 2).

## Why
- **Business value**: Automate workforce variance detection to identify staffing inefficiencies and compliance issues
- **Integration with existing features**: Leverage existing statistical analysis patterns from examples
- **Problems this solves**: Manual review of workforce data, delayed exception identification, inconsistent reporting formats

## What
A Python-based analytics system with CLI interface that processes CSV workforce data, performs statistical analysis using pandas/scipy, and generates professional PDF reports via Playwright.

### Success Criteria
- [ ] Ingest and normalize model data from CSV files with proper date/role handling
- [ ] Calculate descriptive statistics and control limits for each facility/role combination
- [ ] Detect statistical variances using normality tests and appropriate control methods
- [ ] Generate trend analysis with linear regression for trailing windows
- [ ] Compile exceptions into structured DataFrames for reporting
- [ ] Produce professional PDF reports per facility with KPIs, heat-maps, and exception details
- [ ] Include comprehensive logging and error handling throughout
- [ ] Support configurable control variables and thresholds

## All Needed Context

### Documentation & References
```yaml
# MUST READ - Include these in your context window
- url: https://pandas.pydata.org/pandas-docs/stable/
  why: Data manipulation, normalization, and statistical operations
  
- url: https://scipy.org/doc/scipy/reference/stats.html
  why: Statistical tests, normality testing, descriptive statistics
  
- url: https://numpy.org/doc/stable/
  why: Numerical operations, mathematical functions, array handling
  
- url: https://matplotlib.org/stable/users/index.html
  why: Chart generation, statistical plotting, visualization foundations
  
- url: https://seaborn.pydata.org/tutorial.html
  why: Statistical data visualization, heat-maps, trend charts
  
- url: https://playwright.dev/python/
  why: Modern browser automation for PDF generation from HTML
  critical: Handle large datasets efficiently, memory management for reports
  
- url: https://docs.python.org/3/library/asyncio-dev.html
  why: Async patterns for PDF generation, non-blocking operations
  section: Best practices for error handling and task management
  
- file: examples/data_processing.py
  why: Statistical analysis patterns, normality testing, control limit calculations
  critical: Proven patterns for weekly aggregation and variance detection
  
- file: examples/dashboard_generator.py
  why: Report generation workflow, async patterns, directory management
  critical: Established patterns for facility iteration and exception filtering
  
- file: examples/SampleModelData.csv
  why: Model data structure understanding, column mapping requirements
  
- file: examples/SampleFacilityData.csv
  why: Actual hours data structure, employee-level vs aggregated data patterns
```

### Current Codebase tree
```bash
workforce/
├── CLAUDE.md                    # Project rules and conventions
├── INITIAL.md                   # Feature requirements
├── examples/
│   ├── SampleModelData.csv      # Model hours reference data
│   ├── SampleFacilityData.csv   # Actual hours employee data
│   ├── data_processing.py       # Statistical analysis patterns
│   └── dashboard_generator.py   # Report generation patterns
├── PRPs/
│   └── templates/
│       └── prp_base.md         # Template structure
└── input/                      # Data input directory
```

### Desired Codebase tree with files to be added and responsibility of file
```bash
workforce/
├── main.py                     # Main CLI entry point with argument parsing
├── config/
│   ├── __init__.py
│   ├── settings.py             # Control variables and configuration management
│   └── constants.py            # Global constants and enums
├── src/
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── data_models.py      # Pydantic models for data validation
│   │   └── config_models.py    # Pydantic models for configuration
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── model_loader.py     # Model data ingestion (F-1)
│   │   ├── hours_loader.py     # Facility hours ingestion (F-2)
│   │   └── normalizer.py       # Data normalization (F-2)
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── statistics.py       # Descriptive statistics calculation
│   │   ├── variance.py         # Variance detection (F-3a, F-3b)
│   │   └── trends.py          # Trend analysis (F-4)
│   ├── reporting/
│   │   ├── __init__.py
│   │   ├── exceptions.py       # Exception compiler (F-5)
│   │   ├── pdf_generator.py    # PDF report generator (F-6)
│   │   └── templates/          # HTML templates for reports
│   └── utils/
│       ├── __init__.py
│       ├── logging_config.py   # Logging setup (F-7)
│       └── error_handlers.py   # Error handling utilities (F-8)
├── tests/
│   ├── __init__.py
│   ├── test_ingestion/
│   ├── test_analysis/
│   ├── test_reporting/
│   └── fixtures/               # Test data fixtures
├── input/                      # Data input directory
├── output/                     # Generated reports directory
├── logs/                       # Application logs
├── .env.example               # Environment variables template
└── README.md                  # Setup and usage documentation
```

### Known Gotchas of our codebase & Library Quirks
```python
# CRITICAL: Use base virtual environment for all Python commands
# Example: All pytest and package installations must use 'base' environment

# CRITICAL: Playwright requires browser installation (~150MB) on first setup
# Example: Handle this gracefully in deployment and CI/CD with `playwright install chromium`

# CRITICAL: pandas date parsing can be ambiguous with MMDDYYYY format
# Example: Use explicit format strings like pd.to_datetime(df['Date'], format='%m/%d/%Y')

# CRITICAL: scipy.stats.shapiro has sample size limitations (3 <= n <= 5000)
# Example: Truncate large datasets before normality testing

# CRITICAL: asyncio in Playwright requires proper event loop management
# Example: Use asyncio.run() or existing event loop detection

# CRITICAL: File size limits for Pydantic models with large DataFrames
# Example: Stream processing for large datasets, avoid loading entire CSVs into memory

# CRITICAL: Matplotlib/seaborn figure memory management in batch processing
# Example: Always call plt.close() after saving figures to prevent memory leaks
```

## Implementation Blueprint

### Data models and structure

Create the core data models to ensure type safety and consistency.
```python
# Core Pydantic models for data validation and structure
class ControlVariables(BaseModel):
    days_to_drop: int = Field(description="F-0a: Days to drop from oldest date")
    days_to_process: int = Field(description="F-0b: Days to look back from period end")
    new_data_day: int = Field(description="F-0c: Day of week for clean data")
    use_data_day: bool = Field(description="F-0d: Use new data day vs days to drop")
    use_statistics: bool = Field(description="F-0e: Enable statistical abnormality detection")
    variance_threshold: float = Field(description="F-0f: Variance percentage from model")
    weeks_for_control: int = Field(description="F-0g: Weeks for control limit calculation")
    weeks_for_trends: int = Field(description="F-0g: Weeks for trend analysis")

class ModelHours(BaseModel):
    facility: str
    role: str
    model_hours: float
    
class FacilityHours(BaseModel):
    facility: str
    role: str
    date: datetime
    employee_id: Optional[str]
    actual_hours: float
    
class VarianceResult(BaseModel):
    facility: str
    role: str
    date: datetime
    variance_type: str  # "model", "statistical", "trend"
    variance_value: float
    is_exception: bool
    
class StatisticalSummary(BaseModel):
    facility: str
    role: str
    mean: float
    median: float
    std_dev: float
    control_method: str  # "normal" or "mad"
    upper_control_limit: float
    lower_control_limit: float
    is_normal_distribution: bool
```

### list of tasks to be completed to fullfill the PRP in the order they should be completed

```yaml
Task 1: Project Structure and Configuration Setup
CREATE config/settings.py:
  - IMPLEMENT ControlVariables pydantic model with all F-0 parameters
  - ADD environment variable loading with python_dotenv
  - PRESERVE directory path configuration patterns from examples
  - INCLUDE validation for all control parameters

CREATE config/constants.py:
  - DEFINE file path constants and directory structures
  - ADD column mapping dictionaries for CSV ingestion
  - MIRROR patterns from examples/data_processing.py line 36-51

CREATE src/models/data_models.py:
  - IMPLEMENT all pydantic models for data validation
  - ADD proper datetime handling for MMDDYYYY format
  - ENSURE type safety for all numerical fields

Task 2: Data Ingestion Layer (F-1, F-2)
CREATE src/ingestion/model_loader.py:
  - IMPLEMENT load_model_data function mirroring examples pattern
  - ADD CSV validation and column mapping
  - INCLUDE proper error handling for missing files
  - DISPLAY formatted table output as specified in F-1a

CREATE src/ingestion/hours_loader.py:
  - IMPLEMENT load_facility_data function for multi-facility CSV
  - ADD facility separation logic by location key
  - MIRROR column mapping from examples/data_processing.py

CREATE src/ingestion/normalizer.py:
  - IMPLEMENT standardize_datetime for MMDDYYYY format (F-2)
  - ADD convert_hours_to_float function
  - INCLUDE harmonize_role_names for case/spelling consistency
  - PRESERVE existing normalization patterns from examples

Task 3: Statistical Analysis Engine (F-3a, F-3b)
CREATE src/analysis/statistics.py:
  - MIGRATE descriptive_stats_by_role_facility from examples
  - ADD normality testing with shapiro-wilk (handle sample size limits)
  - IMPLEMENT control_limit_calculation with both std and MAD methods
  - ENSURE weekly aggregation patterns from examples line 85-108

CREATE src/analysis/variance.py:
  - IMPLEMENT variance_detection_by_role_day_facility (F-3a)
  - ADD variance_detection_by_employee_role (F-3b)
  - INCLUDE percentage variance checking against model data
  - ADD statistical abnormality flagging with normality consideration
  - MIRROR control violation patterns from examples line 361-391

Task 4: Trend Analysis Implementation (F-4)
CREATE src/analysis/trends.py:
  - IMPLEMENT trailing_window_analysis function
  - ADD linear regression slope and p-value calculation using scipy
  - INCLUDE per facility/role trend detection
  - ENSURE integration with variance detection system

Task 5: Exception Management (F-5)
CREATE src/reporting/exceptions.py:
  - IMPLEMENT compile_exceptions function
  - ADD DataFrame aggregation of all flagged variances
  - INCLUDE exception categorization (model, statistical, trend)
  - ENSURE tidy format ready for reporting

Task 6: PDF Report Generation (F-6)
CREATE src/reporting/pdf_generator.py:
  - IMPLEMENT generate_facility_report function with async patterns
  - ADD HTML template rendering with cover page (F-6a)
  - INCLUDE KPI summary table generation (F-6b)
  - ADD variance heat-map and trend chart creation (F-6c)
  - INCLUDE detailed exception list formatting (F-6d)
  - MIRROR async patterns from examples/dashboard_generator.py line 63-182

CREATE src/reporting/templates/:
  - ADD facility_report.html template with professional styling
  - INCLUDE responsive design for PDF rendering
  - ADD chart embedding and table formatting

Task 7: Utility Infrastructure (F-7, F-8)
CREATE src/utils/logging_config.py:
  - IMPLEMENT comprehensive logging setup
  - ADD file and console handlers
  - INCLUDE structured logging for troubleshooting

CREATE src/utils/error_handlers.py:
  - IMPLEMENT custom exception classes
  - ADD graceful error handling decorators
  - INCLUDE exit code management

Task 8: Main Application and CLI
CREATE main.py:
  - IMPLEMENT CLI argument parsing
  - ADD main execution flow orchestration
  - INCLUDE progress reporting and status updates
  - ENSURE proper error handling and exit codes

Task 9: Testing Infrastructure
CREATE tests/test_ingestion/:
  - ADD unit tests for model and hours loading
  - INCLUDE edge cases for malformed data
  - ADD validation tests for data normalization

CREATE tests/test_analysis/:
  - ADD statistical calculation verification tests
  - INCLUDE control limit accuracy tests
  - ADD trend analysis validation

CREATE tests/test_reporting/:
  - ADD PDF generation tests
  - INCLUDE template rendering validation
  - ADD exception compilation tests

Task 10: Documentation and Setup
CREATE .env.example:
  - ADD all required environment variables
  - INCLUDE configuration examples
  - ADD deployment considerations

UPDATE README.md:
  - ADD comprehensive setup instructions
  - INCLUDE usage examples and CLI documentation
  - ADD project structure overview
  - INCLUDE troubleshooting guide
```

### Per task pseudocode as needed added to each task

```python
# Task 2: Data Ingestion - Model Loader
def load_model_data(file_path: str) -> pd.DataFrame:
    """Load and validate model hours data (F-1)"""
    # PATTERN: File existence check from examples/data_processing.py:30
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Model data file not found: {file_path}")
    
    # PATTERN: CSV loading with column validation
    df = pd.read_csv(file_path)
    required_columns = ['LOCATION_KEY', 'LOCATION_NAME', 'STAFF_ROLE_NAME', 'TOTAL_HOURS']
    
    # CRITICAL: Validate all required columns exist
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing columns: {missing_cols}")
    
    # PATTERN: Column mapping and normalization from examples
    df = df.rename(columns=MODEL_COLUMN_MAPPING)
    df['ModelHours'] = df['TOTAL_HOURS'].astype(float)
    
    # F-1a: Display formatted table
    display_model_table(df)
    return df

# Task 3: Statistical Analysis - Variance Detection
def detect_variances_by_role_day_facility(df: pd.DataFrame, model_df: pd.DataFrame, 
                                        control_vars: ControlVariables) -> pd.DataFrame:
    """Detect variances for each Role × Day × Facility combination (F-3a)"""
    results = []
    
    for facility in df['Facility'].unique():
        for role in df['Role'].unique():
            # PATTERN: Data filtering from examples/data_processing.py:167-177
            subset = df[(df['Facility'] == facility) & (df['Role'] == role)]
            
            if not subset.empty:
                # CRITICAL: Calculate descriptive statistics
                stats = calculate_descriptive_stats(subset['ActualHours'])
                
                # PATTERN: Normality testing from examples line 243-256
                is_normal = test_normality(subset['ActualHours'])
                
                # CRITICAL: Choose appropriate control method
                if is_normal:
                    control_limits = calculate_normal_control_limits(stats)
                else:
                    control_limits = calculate_mad_control_limits(stats)
                
                # PATTERN: Model variance checking
                model_hours = get_model_hours(model_df, facility, role)
                model_variance = calculate_model_variance(stats['mean'], model_hours, 
                                                        control_vars.variance_threshold)
                
                # PATTERN: Statistical abnormality flagging
                if control_vars.use_statistics:
                    statistical_exceptions = detect_statistical_exceptions(subset, control_limits)
                    
                # PATTERN: Trend analysis integration
                trend_exceptions = detect_trend_exceptions(subset, control_vars.weeks_for_trends)
                
                results.append(compile_variance_result(facility, role, model_variance, 
                                                     statistical_exceptions, trend_exceptions))
    
    return pd.DataFrame(results)

# Task 6: PDF Generation - Report Builder
async def generate_facility_pdf_report(facility: str, exceptions_df: pd.DataFrame, 
                                     stats_df: pd.DataFrame, output_dir: str) -> str:
    """Generate comprehensive PDF report for facility (F-6)"""
    # PATTERN: Async browser automation from examples/dashboard_generator.py
    browser = await launch(headless=True, args=['--no-sandbox'])
    page = await browser.newPage()
    
    try:
        # F-6a: Cover page with date range
        cover_html = render_cover_page(facility, get_date_range(exceptions_df))
        
        # F-6b: KPI summary table
        kpi_html = render_kpi_summary(calculate_facility_kpis(stats_df, facility))
        
        # F-6c: Variance heat-map & trend charts
        heatmap_html = generate_variance_heatmap(exceptions_df, facility)
        trend_html = generate_trend_charts(stats_df, facility)
        
        # F-6d: Detailed exception list
        exceptions_html = render_exception_details(exceptions_df, facility)
        
        # PATTERN: HTML assembly and PDF generation
        full_html = assemble_report_html(cover_html, kpi_html, heatmap_html, 
                                       trend_html, exceptions_html)
        
        await page.setContent(full_html)
        
        # CRITICAL: PDF generation with proper formatting
        pdf_path = os.path.join(output_dir, f"{facility}_report.pdf")
        await page.pdf({
            'path': pdf_path,
            'format': 'A4',
            'margin': {'top': '1in', 'bottom': '1in', 'left': '1in', 'right': '1in'},
            'printBackground': True
        })
        
        return pdf_path
        
    finally:
        await browser.close()
```

### Integration Points
```yaml
DATABASE:
  - input_files: "SampleModelData.csv and SampleFacilityData.csv processing"
  - data_validation: "Pydantic models ensure type safety and data integrity"
  
CONFIG:
  - add to: config/settings.py
  - pattern: "CONTROL_VARIABLES = ControlVariables(**env_vars)"
  - env_file: ".env with all F-0 parameters"
  
LOGGING:
  - add to: src/utils/logging_config.py
  - pattern: "Structured logging with facility/role context"
  - output: "logs/workforce_analytics.log with rotation"
  
REPORTS:
  - add to: output/reports/
  - pattern: "{facility_name}_{date_range}.pdf per facility"
  - exceptions_only: "Generate reports only for facilities with exceptions if configured"
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# Run these FIRST - fix any errors before proceeding
uv run ruff check --fix src/ config/ tests/  # Auto-fix style issues
uv run mypy src/ config/                      # Type checking

# Expected: No errors. If errors, READ the error message and fix the root cause.
```

### Level 2: Unit Tests each new feature/file/function use existing test patterns
```python
# CREATE comprehensive test coverage for each module:

def test_model_data_loading_happy_path():
    """Test successful model data loading with valid CSV"""
    result_df = load_model_data("tests/fixtures/sample_model.csv")
    assert not result_df.empty
    assert 'ModelHours' in result_df.columns
    assert result_df['ModelHours'].dtype == float

def test_variance_detection_with_exceptions():
    """Test variance detection identifies statistical exceptions"""
    test_data = create_test_facility_data_with_outliers()
    variances = detect_variances_by_role_day_facility(test_data, test_model_data, test_control_vars)
    assert len(variances[variances['is_exception'] == True]) > 0

def test_pdf_generation_creates_valid_file():
    """Test PDF generation produces readable output"""
    test_exceptions = create_test_exceptions_dataframe()
    pdf_path = await generate_facility_pdf_report("Test Facility", test_exceptions, test_stats, "/tmp")
    assert os.path.exists(pdf_path)
    assert os.path.getsize(pdf_path) > 1000  # Ensure non-empty PDF

def test_control_limit_calculation_normality_handling():
    """Test control limits use appropriate method based on normality"""
    normal_data = generate_normal_distribution_data()
    non_normal_data = generate_skewed_distribution_data()
    
    normal_limits = calculate_control_limits(normal_data)
    non_normal_limits = calculate_control_limits(non_normal_data)
    
    assert normal_limits['method'] == 'normal'
    assert non_normal_limits['method'] == 'mad'

def test_data_normalization_edge_cases():
    """Test data normalization handles malformed dates and hours"""
    malformed_data = create_malformed_test_data()
    with pytest.raises(ValidationError):
        normalize_facility_data(malformed_data)
```

```bash
# Run and iterate until passing:
uv run pytest tests/ -v --cov=src/
# Target: >90% code coverage, all tests passing
# If failing: Read error, understand root cause, fix code, re-run tests
```

### Level 3: Integration Test
```bash
# Test the complete workflow with sample data
uv run python main.py --input examples/SampleFacilityData.csv --model examples/SampleModelData.csv --output output/test_run

# Expected outputs:
# - Console output with descriptive statistics tables
# - PDF reports in output/test_run/ directory
# - Log files in logs/ directory
# - No exceptions or error exit codes

# Validate generated PDFs contain:
# - Cover page with correct date range
# - KPI summary table with numerical data
# - Variance heat-map with visual indicators
# - Exception list with specific violations

# Test error handling:
uv run python main.py --input nonexistent.csv
# Expected: Graceful error message and non-zero exit code
```

## Final validation Checklist
- [ ] All tests pass: `uv run pytest tests/ -v --cov=src/`
- [ ] No linting errors: `uv run ruff check src/ config/`
- [ ] No type errors: `uv run mypy src/ config/`
- [ ] Sample data processing successful: `python main.py --input examples/SampleFacilityData.csv`
- [ ] PDF reports generated with proper formatting and content
- [ ] Exception detection identifies statistical outliers correctly
- [ ] Logging captures all important events and errors
- [ ] Memory usage reasonable for large datasets
- [ ] Error cases handled gracefully with meaningful messages
- [ ] Documentation complete and accurate

---

## Anti-Patterns to Avoid
- ❌ Don't load entire large CSVs into memory - use chunked processing
- ❌ Don't skip normality testing - it determines the statistical method
- ❌ Don't generate PDFs for all facilities if exceptions-only mode is enabled
- ❌ Don't use blocking operations in async PDF generation
- ❌ Don't hardcode file paths - use configuration management
- ❌ Don't ignore matplotlib memory leaks - always close figures
- ❌ Don't skip data validation - use Pydantic models consistently

## Quality Assessment Score: 9/10

**Confidence Level for One-Pass Implementation**: High

**Strengths**:
- Comprehensive context from existing statistical analysis examples
- Clear task breakdown with specific implementation patterns
- Robust validation loops with real data testing
- Proven libraries and established patterns
- Detailed error handling and edge case considerations

**Minor Considerations**:
- Large dataset memory management may require iterative optimization
- PDF rendering performance with complex charts may need tuning

This PRP provides complete context for implementing a production-ready workforce analytics system with statistical rigor and professional reporting capabilities.