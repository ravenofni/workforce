# Workforce Analytics System

A comprehensive Python-based analytics system that ingests workforce model hours vs actual hours data, performs statistical variance detection, generates reports, and produces facility-specific PDF reports highlighting exceptions and trends.

## 🚀 Quick Start

```bash
# 1. Clone and setup
git clone <repository-url>
cd workforce

# 2. Create virtual environment
python -m venv base
source base/bin/activate  # On Windows: base\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install Playwright browsers (required for PDF generation)
playwright install chromium

# 5. Copy environment template
cp .env.example .env

# 6. Run analysis with sample data
python main.py --facility-data examples/SampleFacilityData.csv --model-data examples/SampleModelData.csv
```

## 📊 Features

### Core Functionality
- **F-1**: Model data ingestion with formatted table display
- **F-2**: Multi-facility hours data ingestion with normalization
- **F-3a**: Variance detection by Role × Day × Facility combinations
- **F-3b**: Variance detection by Employee × Role combinations  
- **F-4**: Trend analysis with linear regression
- **F-5**: Exception compilation into structured reports
- **F-6**: PDF report generation with charts and professional styling
- **F-7**: Comprehensive logging system
- **F-8**: Robust error handling

### Statistical Analysis
- **Normality Testing**: Shapiro-Wilk test with sample size handling
- **Control Limits**: Automatic selection of normal vs MAD methods
- **Model Variance Detection**: Configurable percentage thresholds
- **Statistical Control**: Upper/lower control limit violations
- **Trend Detection**: Linear regression with significance testing

### Data Processing
- **F-0 Control Variables**: Dynamic date range calculation with configurable parameters
- **Sunday=1 Day Convention**: Day-of-week numbering matches upstream systems (Sunday=1, Monday=2, etc.)
- **MMDDYYYY Date Handling**: Explicit format parsing with flexible fallback
- **Multi-facility Support**: CSV files with location key separation
- **Weekly Aggregation**: Sunday-Saturday weekly data summaries
- **Role Name Harmonization**: Consistent naming and case handling
- **Memory Efficient**: Large dataset handling with chunked processing

## 📁 Project Structure

```
workforce/
├── main.py                     # Main CLI application entry point
├── config/
│   ├── settings.py             # Configuration management with Pydantic
│   └── constants.py            # Column mappings and constants
├── src/
│   ├── models/
│   │   └── data_models.py      # Pydantic models for type safety
│   ├── ingestion/
│   │   ├── model_loader.py     # Model hours data loading (F-1)
│   │   ├── hours_loader.py     # Facility hours data loading (F-2)  
│   │   └── normalizer.py       # Data standardization (F-2)
│   ├── analysis/
│   │   ├── statistics.py       # Descriptive statistics & control limits
│   │   ├── variance.py         # Variance detection (F-3a, F-3b)
│   │   └── trends.py          # Trend analysis (F-4)
│   ├── reporting/
│   │   ├── exceptions.py       # Exception compilation (F-5)
│   │   ├── chart_generator.py  # Chart generation with matplotlib/seaborn
│   │   ├── pdf_generator.py    # PDF report generation (F-6)
│   │   ├── report_orchestrator.py # Report coordination and management
│   │   └── templates/          # HTML templates for PDF reports
│   │       └── facility_report.html # Professional facility report template
│   └── utils/
│       ├── date_calculator.py  # F-0 control variables date calculation
│       ├── logging_config.py   # Comprehensive logging (F-7)
│       └── error_handlers.py   # Error handling (F-8)
├── examples/
│   ├── SampleModelData.csv     # Sample model hours data
│   ├── SampleFacilityData.csv  # Sample facility hours data
│   ├── data_processing.py      # Reference statistical patterns
│   └── dashboard_generator.py  # Reference reporting patterns
├── tests/                      # Unit test suite (planned)
├── output/                     # Generated reports directory
├── logs/                       # Application logs
├── .env.example               # Environment configuration template
└── README.md                  # This file
```

## 🔧 Configuration

The system uses environment variables for configuration. Copy `.env.example` to `.env` and adjust:

### Control Variables (F-0)
```bash
# F-0a: Days to drop from oldest date back
DAYS_TO_DROP=7

# F-0b: Days to look back from period end date  
DAYS_TO_PROCESS=84

# F-0c: Day of week for clean data (1=Sunday, 2=Monday, 7=Saturday)
NEW_DATA_DAY=1

# F-0d: Use new data day vs days to drop
USE_DATA_DAY=true

# F-0e: Enable statistical abnormality detection
USE_STATISTICS=true

# F-0f: Variance percentage threshold for model exceptions
VARIANCE_THRESHOLD=15.0

# F-0g: Weeks for control limit calculation
WEEKS_FOR_CONTROL=12

# F-0g: Weeks for trend analysis  
WEEKS_FOR_TRENDS=8
```

## 📖 Usage

### Quick Start (Debug Mode)
```bash
# Use default sample data files - fastest way to test the system
python main.py --debug
```

### Basic Analysis
```bash
python main.py --facility-data data/hours.csv --model-data data/model.csv
```

### Advanced Options
```bash
# Debug mode with custom settings
python main.py --debug --exceptions-only --display-only

# Generate reports only for facilities with exceptions
python main.py --facility-data data/hours.csv --model-data data/model.csv --exceptions-only

# Override configuration parameters
python main.py --facility-data data/hours.csv --model-data data/model.csv \
  --variance-threshold 20.0 \
  --weeks-for-control 16 \
  --weeks-for-trends 12

# Analyze specific date range
python main.py --facility-data data/hours.csv --model-data data/model.csv \
  --analysis-start-date 2025-05-01 \
  --analysis-end-date 2025-05-31

# Export results to CSV
python main.py --facility-data data/hours.csv --model-data data/model.csv --export-csv

# Display analysis only (no PDF generation)
python main.py --facility-data data/hours.csv --model-data data/model.csv --display-only

# Debugging with verbose logging (debug mode enables DEBUG automatically)
python main.py --facility-data data/hours.csv --model-data data/model.csv --log-level DEBUG
```

### Command Line Options

**Note**: All command line arguments can be set via environment variables in a `.env` file.

```
Data Input (can be set via .env):
  --facility-data PATH      CSV file with facility hours data (actual hours)
                           Environment: FACILITY_DATA_PATH
  --model-data PATH         CSV file with model hours data (expected hours)
                           Environment: MODEL_DATA_PATH
  --debug                   Use default sample data files (examples/*.csv)
                           Environment: DEBUG_MODE=true

Analysis Control:
  --output-dir DIR          Output directory for reports (default: output)
                           Environment: OUTPUT_DIR
  --exceptions-only         Generate reports only for facilities with exceptions
                           Environment: EXCEPTIONS_ONLY=true
  --weeks-for-control N     Override weeks for control limit calculation
                           Environment: WEEKS_FOR_CONTROL
  --weeks-for-trends N      Override weeks for trend analysis
                           Environment: WEEKS_FOR_TRENDS
  --variance-threshold N    Override variance percentage threshold
                           Environment: VARIANCE_THRESHOLD

Date Range Control:
  --analysis-start-date YYYY-MM-DD  Override analysis start date
                                   Environment: ANALYSIS_START_DATE
  --analysis-end-date YYYY-MM-DD    Override analysis end date  
                                   Environment: ANALYSIS_END_DATE

Output Control:
  --display-only           Only display results, don't generate PDFs
                           Environment: DISPLAY_ONLY=true
  --export-csv             Export exception data to CSV files
                           Environment: EXPORT_CSV=true
  --log-level LEVEL        Set logging level (DEBUG, INFO, WARNING, ERROR)
                           Environment: LOG_LEVEL
  --log-dir DIR            Directory for log files (default: logs)
                           Environment: LOGS_DIR
  --quiet                  Suppress console output
                           Environment: QUIET=true
```

### Environment Variable Configuration

Create a `.env` file in the project root to set default values:

```bash
# Copy the example file
cp .env.example .env

# Edit with your preferred defaults
nano .env
```

Example `.env` configuration:
```bash
FACILITY_DATA_PATH=data/my_facility_data.csv
MODEL_DATA_PATH=data/my_model_data.csv
DEBUG_MODE=false
OUTPUT_DIR=my_reports
LOG_LEVEL=INFO
EXCEPTIONS_ONLY=true
DISPLAY_ONLY=false
```

**Priority Order**: Command line arguments > Environment variables > Built-in defaults

### VS Code Development Configurations

For development and testing, VS Code launch.json configurations are provided in `.vscode/launch.json`:

- **Debug - Default (Dynamic Calculation)** - Tests automatic F-0 date calculation
- **Debug - Weekly Test Period** - Tests specific 1-week analysis period  
- **Debug - Monthly Test Period** - Tests 1-month analysis period
- **Debug - Custom Date Range** - Tests custom date range scenario
- **Debug - Display Only (No PDF)** - Fast testing without PDF generation
- **Production - Dynamic Calculation** - Simulates production environment

These configurations eliminate the need for hard-coded date constants while providing comprehensive testing scenarios.

## 📊 Data Format

### Model Data CSV Format
```csv
LOCATION_KEY,LOCATION_NAME,HOURS_DATE,DAY_OF_WEEK,DAY_NUMBER,TOTAL_HOURS,STAFF_ROLE_NAME,WORKFORCE_MODEL_ROLE_SORT,COST_CENTER_SORT
183,Ansley Park,7/7/24,Sunday,1,0,Director of Nursing,1,1
183,Ansley Park,7/7/24,Sunday,1,12,Nursing Supervisor Wknd (RN),1,6
```

### Facility Data CSV Format  
```csv
LOCATION_KEY,LOCATION_NAME,HOURS_DATE,DAY_OF_WEEK,DAY_NUMBER,EMPLOYEE_ID,EMPLOYEE_NAME,TOTAL_HOURS,STAFF_ROLE_NAME,WORKFORCE_MODEL_ROLE_SORT,COST_CENTER_SORT
183,Ansley Park,5/4/25,Sunday,1,141093,Loretta Cross,14.78,Charge Nurse (LPN),1,7
183,Ansley Park,5/4/25,Sunday,1,146182,Shannae M King,7.67,Charge Nurse (LPN),1,7
```

## 🔍 Analysis Output

The system provides comprehensive analysis output:

### Console Display
- **Model Data Summary**: F-1a formatted table display
- **Descriptive Statistics**: Mean, median, control limits by facility/role
- **Variance Detection Summary**: Model, statistical, and trend exceptions
- **Trend Analysis Summary**: Significant trends with statistical measures
- **Exception Compilation**: Aggregated exceptions ready for reporting

### Log Files
- **Main Log**: `logs/workforce_analytics.log` with rotation
- **Session Logs**: Detailed per-run logging with facility/role context
- **Performance Metrics**: Processing rates and memory usage

### Export Files (with --export-csv)
- **exceptions.csv**: All detected exceptions with details
- **statistics_summary.csv**: Statistical summary by facility/role

### PDF Reports (F-6)
- **Cover Page**: Facility name, analysis period, generation timestamp
- **Executive Summary**: KPI cards with key metrics and overall assessment
- **Visual Analysis**: Charts including variance heat-maps, trend analysis, control limits
- **Exception Details**: Comprehensive table of all exceptions with severity ratings
- **Statistical Summary**: Control limits and normality testing results by role

## 🧪 Statistical Methods

### Normality Testing
- **Shapiro-Wilk Test**: Automatic normality assessment
- **Sample Size Handling**: Truncation for scipy limitations (n ≤ 5000)
- **Method Selection**: Normal distribution vs MAD-based methods

### Control Limits
- **Normal Data**: Mean ± 3σ control limits
- **Non-normal Data**: Median ± 3×MAD control limits  
- **Lower Bound Protection**: Hours cannot be negative

### Variance Detection
- **Model Variance**: Percentage deviation from expected hours
- **Statistical Control**: Upper/lower control limit violations
- **Trend Analysis**: Linear regression with significance testing

## 🛠 Development

### Code Quality
- **Type Safety**: Comprehensive Pydantic models
- **Error Handling**: Custom exceptions with exit codes
- **Logging**: Structured logging with context filters
- **Memory Management**: Efficient pandas operations

### Testing (Planned)
```bash
# Run unit tests
uv run pytest tests/ -v --cov=src/

# Style checking  
uv run ruff check --fix src/ config/ tests/

# Type checking
uv run mypy src/ config/
```

### Architecture Patterns
- **Modular Design**: Clear separation of concerns
- **Configuration Management**: Environment-based settings
- **Data Validation**: Pydantic model validation
- **Error Recovery**: Graceful degradation and reporting

## 📋 Requirements

### Python Dependencies
- **pandas**: Data manipulation and analysis
- **scipy**: Statistical functions and normality testing
- **numpy**: Numerical operations and mathematical functions
- **pydantic**: Data validation and settings management
- **python-dotenv**: Environment variable management

### PDF Generation Dependencies
- **playwright**: Modern browser automation for PDF generation
- **matplotlib**: Chart generation and statistical plotting
- **seaborn**: Advanced statistical data visualization
- **jinja2**: HTML template rendering system

### System Requirements
- **Python 3.8+**: Modern Python with typing support
- **Memory**: 2GB+ for large datasets
- **Storage**: Adequate space for logs and reports

## 🔮 Roadmap

### Phase 1: Core Analytics ✅
- [x] Data ingestion and normalization
- [x] Statistical analysis engine
- [x] Variance detection (F-3a, F-3b)
- [x] Trend analysis (F-4)
- [x] Exception compilation (F-5)
- [x] CLI interface and logging

### Phase 2: Report Generation ✅
- [x] HTML template system with Jinja2
- [x] Chart generation with matplotlib/seaborn
- [x] PDF conversion with Playwright
- [x] Per-facility report generation (F-6)
- [x] Professional styling and formatting

### Phase 2.5: Date Calculation & Production Safety ✅
- [x] F-0 control variables implementation
- [x] Dynamic date range calculation
- [x] Sunday=1 day-of-week convention
- [x] Command line date overrides
- [x] VS Code development configurations
- [x] Production safety (eliminated constants)

### Phase 3 (Future): Real-time Capabilities
- [ ] Interactive HTML dashboards
- [ ] Real-time data processing
- [ ] Web interface for configuration
- [ ] API endpoints for integration

## 🤝 Contributing

This system follows context engineering principles with comprehensive documentation and examples. See the examples/ directory for implementation patterns and the PRP workflow for structured development.

## 📄 License

[Add your license information here]