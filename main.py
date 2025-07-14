"""
Main CLI entry point for the Workforce Analytics System.
Orchestrates the complete analysis pipeline from data ingestion to report generation.
"""

import argparse
import sys
import os
import asyncio
from datetime import datetime
from typing import List

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Load environment variables early
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not available, environment variables can still be set manually
    pass

from config.settings import get_settings, ensure_directories
from config.constants import DEFAULT_FACILITY_DATA_PATH, DEFAULT_MODEL_DATA_PATH, FileColumns
from src.utils.logging_config import setup_logging, TimedOperation
from src.utils.error_handlers import handle_exceptions, ExitCode, WorkforceAnalyticsError
from src.ingestion.model_loader import load_model_data
from src.ingestion.hours_loader import load_facility_data, aggregate_to_weekly
from src.ingestion.normalizer import normalize_all_data
from src.analysis.statistics import calculate_facility_role_statistics, display_statistics_table
from src.analysis.variance import detect_all_variances, display_variance_summary
from src.analysis.trends import analyze_trends_for_all_facilities, display_trend_summary
from src.reporting.exceptions import compile_exceptions, display_exceptions_summary
from src.reporting.report_orchestrator import generate_comprehensive_reports
from src.reporting.pdf_generator import check_pdf_generation_availability
from src.models.data_models import DataQualityException


def get_env_default(env_var: str, default_value, value_type=str):
    """
    Get environment variable with type conversion and fallback to default.
    
    Args:
        env_var: Environment variable name
        default_value: Default value if env var not set
        value_type: Type to convert to (str, int, float, bool)
        
    Returns:
        Converted value or default
    """
    env_value = os.getenv(env_var)
    if env_value is None:
        return default_value
    
    try:
        if value_type == bool:
            return env_value.lower() in ('true', '1', 'yes', 'on')
        elif value_type == int:
            return int(env_value)
        elif value_type == float:
            return float(env_value)
        else:
            return str(env_value)
    except (ValueError, TypeError):
        return default_value


def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments.
    
    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Workforce Analytics System - Analyze model vs actual hours with statistical variance detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --debug                                          # Quick start with sample data
  python main.py --facility-data examples/SampleFacilityData.csv --model-data examples/SampleModelData.csv
  python main.py --facility-data data/hours.csv --model-data data/model.csv --output-dir reports/
  python main.py --debug --exceptions-only --display-only        # Debug mode, no PDFs
  python main.py                                                  # Use defaults from .env file

Note: All arguments can be set via environment variables in .env file.
Environment variables: FACILITY_DATA_PATH, MODEL_DATA_PATH, DEBUG_MODE, OUTPUT_DIR, etc.
        """
    )
    
    # Input arguments
    parser.add_argument(
        '--facility-data', 
        required=False,
        default=get_env_default('FACILITY_DATA_PATH', None),
        help='Path to CSV file containing facility hours data (actual hours worked)'
    )
    
    parser.add_argument(
        '--model-data',
        required=False,
        default=get_env_default('MODEL_DATA_PATH', None),
        help='Path to CSV file containing model hours data (expected hours)'
    )
    
    # Debug mode argument
    parser.add_argument(
        '--debug',
        action='store_true',
        default=get_env_default('DEBUG_MODE', False, bool),
        help='Enable debug mode with default sample data files and enhanced logging'
    )
    
    # Output arguments
    parser.add_argument(
        '--output-dir',
        default=get_env_default('OUTPUT_DIR', 'output'),
        help='Directory for generated reports and analysis files (default: output)'
    )
    
    # Analysis control arguments
    parser.add_argument(
        '--exceptions-only',
        action='store_true',
        default=get_env_default('EXCEPTIONS_ONLY', False, bool),
        help='Generate reports only for facilities with exceptions'
    )
    
    parser.add_argument(
        '--weeks-for-control',
        type=int,
        default=get_env_default('WEEKS_FOR_CONTROL', None, int),
        help='Number of weeks for control limit calculation (overrides config)'
    )
    
    parser.add_argument(
        '--weeks-for-trends', 
        type=int,
        default=get_env_default('WEEKS_FOR_TRENDS', None, int),
        help='Number of weeks for trend analysis (overrides config)'
    )
    
    parser.add_argument(
        '--variance-threshold',
        type=float,
        default=get_env_default('VARIANCE_THRESHOLD', None, float),
        help='Variance percentage threshold for model exceptions (overrides config)'
    )
    
    # Operation mode arguments
    parser.add_argument(
        '--display-only',
        action='store_true',
        default=get_env_default('DISPLAY_ONLY', False, bool),
        help='Only display analysis results, do not generate PDF reports'
    )
    
    parser.add_argument(
        '--export-csv',
        action='store_true',
        default=get_env_default('EXPORT_CSV', False, bool),
        help='Export exception data to CSV files'
    )
    
    # Logging and debugging
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default=get_env_default('LOG_LEVEL', 'INFO'),
        help='Set logging level (default: INFO)'
    )
    
    parser.add_argument(
        '--log-dir',
        default=get_env_default('LOGS_DIR', 'logs'),
        help='Directory for log files (default: logs)'
    )
    
    parser.add_argument(
        '--quiet',
        action='store_true',
        default=get_env_default('QUIET', False, bool),
        help='Suppress console output (logs only to file)'
    )
    
    # Version
    parser.add_argument(
        '--version',
        action='version',
        version='Workforce Analytics System 1.0.0'
    )
    
    return parser.parse_args()


def display_data_quality_summary(exceptions: List[DataQualityException]) -> None:
    """
    Display summary of data quality issues found during normalization.
    
    Args:
        exceptions: List of data quality exceptions to summarize
    """
    if not exceptions:
        return
    
    print("\n" + "="*80)
    print("DATA QUALITY ISSUES SUMMARY")
    print("="*80)
    
    # Group by issue type
    issues_by_type = {}
    issues_by_severity = {}
    facilities_affected = set()
    
    for exc in exceptions:
        issues_by_type[exc.issue_type] = issues_by_type.get(exc.issue_type, 0) + 1
        issues_by_severity[exc.severity] = issues_by_severity.get(exc.severity, 0) + 1
        if exc.facility:
            facilities_affected.add(exc.facility)
    
    print(f"Total Issues Found: {len(exceptions)}")
    print(f"Facilities Affected: {len(facilities_affected)}")
    
    if facilities_affected:
        print(f"  - {', '.join(sorted(facilities_affected))}")
    
    print(f"\nIssues by Type:")
    for issue_type, count in sorted(issues_by_type.items()):
        print(f"  - {issue_type.replace('_', ' ').title()}: {count}")
    
    print(f"\nIssues by Severity:")
    severity_order = ['low', 'medium', 'high', 'critical']
    for severity in severity_order:
        if severity in issues_by_severity:
            print(f"  - {severity.title()}: {issues_by_severity[severity]}")
    
    # Show sample issues
    print(f"\nSample Issues (first 5):")
    for i, exc in enumerate(exceptions[:5]):
        print(f"  {i+1}. {exc.description}")
        if exc.suggested_action:
            print(f"     Action: {exc.suggested_action}")
    
    if len(exceptions) > 5:
        print(f"     ... and {len(exceptions) - 5} more issues")
    
    print("\nNote: All data quality issues are captured for reporting.")
    print("Problematic values have been corrected for analysis continuity.")
    print("="*80 + "\n")


@handle_exceptions(exit_on_error=True, log_traceback=True)
def main():
    """
    Main application entry point.
    """
    # Parse command line arguments
    args = parse_arguments()
    
    # Handle debug mode and default file paths
    if args.debug:
        # Enable debug logging if debug mode is set
        if args.log_level == 'INFO':  # Only override if not explicitly set
            args.log_level = 'DEBUG'
        
        # Use default file paths if not provided
        if not args.facility_data:
            args.facility_data = DEFAULT_FACILITY_DATA_PATH
        if not args.model_data:
            args.model_data = DEFAULT_MODEL_DATA_PATH
            
        print("🐛 DEBUG MODE ENABLED")
        print(f"📁 Using facility data: {args.facility_data}")
        print(f"📁 Using model data: {args.model_data}")
        print(f"📋 Log level: {args.log_level}")
        print()
    
    # Validate that data files are provided (either explicitly or via debug mode)
    if not args.facility_data or not args.model_data:
        print("❌ Error: Facility data and model data files are required.")
        print("Either provide both --facility-data and --model-data arguments,")
        print("or use --debug flag to use default sample data files.")
        print()
        print("Examples:")
        print("  python main.py --debug                                    # Use sample data")
        print("  python main.py --facility-data data.csv --model-data model.csv  # Use custom data")
        sys.exit(1)
    
    # Load and update settings
    settings = get_settings()
    
    # Override settings with command line arguments
    if args.weeks_for_control:
        settings.control_variables.weeks_for_control = args.weeks_for_control
    if args.weeks_for_trends:
        settings.control_variables.weeks_for_trends = args.weeks_for_trends
    if args.variance_threshold:
        settings.control_variables.variance_threshold = args.variance_threshold
    if args.exceptions_only:
        settings.generate_only_exceptions = args.exceptions_only
    
    # Update directory settings
    settings.directories.output_dir = args.output_dir
    settings.directories.reports_dir = os.path.join(args.output_dir, 'reports')
    settings.directories.logs_dir = args.log_dir
    
    # Ensure directories exist
    ensure_directories(settings)
    
    # Setup logging
    logger = setup_logging(
        log_level=args.log_level,
        log_dir=args.log_dir,
        console_output=not args.quiet
    )
    
    logger.info("=" * 80)
    logger.info("WORKFORCE ANALYTICS SYSTEM - STARTING ANALYSIS")
    logger.info("=" * 80)
    logger.info(f"Facility Data: {args.facility_data}")
    logger.info(f"Model Data: {args.model_data}")
    logger.info(f"Output Directory: {args.output_dir}")
    logger.info(f"Control Variables: weeks_control={settings.control_variables.weeks_for_control}, "
               f"weeks_trends={settings.control_variables.weeks_for_trends}, "
               f"variance_threshold={settings.control_variables.variance_threshold}%")
    
    # Validate input files
    if not os.path.exists(args.facility_data):
        raise WorkforceAnalyticsError(
            f"Facility data file not found: {args.facility_data}",
            ExitCode.FILE_NOT_FOUND,
            {'file_path': args.facility_data}
        )
    
    if not os.path.exists(args.model_data):
        raise WorkforceAnalyticsError(
            f"Model data file not found: {args.model_data}",
            ExitCode.FILE_NOT_FOUND,
            {'file_path': args.model_data}
        )
    
    # Step 1: Data Ingestion
    logger.info("Step 1: Data Ingestion")
    
    with TimedOperation(logger, "Model Data Loading"):
        model_df, model_loader_exceptions = load_model_data(args.model_data)
        logger.info(f"Loaded {len(model_df)} model records from {model_df[FileColumns.MODEL_LOCATION_NAME].nunique()} facilities")
        logger.info(f"Model data loading captured {len(model_loader_exceptions)} data quality issues")
    
    with TimedOperation(logger, "Facility Data Loading"):
        facility_df, facility_loader_exceptions = load_facility_data(args.facility_data)
        logger.info(f"Loaded {len(facility_df)} facility records from {facility_df[FileColumns.FACILITY_LOCATION_NAME].nunique()} facilities")
        logger.info(f"Facility data loading captured {len(facility_loader_exceptions)} data quality issues")
    
    # Step 2: Data Normalization
    logger.info("Step 2: Data Normalization")
    
    with TimedOperation(logger, "Data Normalization"):
        normalized_facility_df, facility_data_quality_exceptions = normalize_all_data(
            facility_df,
            date_columns=[FileColumns.FACILITY_HOURS_DATE],
            hours_columns=[FileColumns.FACILITY_TOTAL_HOURS],
            facility_col=FileColumns.FACILITY_LOCATION_NAME,
            role_col=FileColumns.FACILITY_STAFF_ROLE_NAME,
            employee_col=FileColumns.FACILITY_EMPLOYEE_ID
        )
        normalized_model_df, model_data_quality_exceptions = normalize_all_data(
            model_df,
            date_columns=[FileColumns.MODEL_HOURS_DATE] if FileColumns.MODEL_HOURS_DATE in model_df.columns else [],
            hours_columns=[FileColumns.MODEL_TOTAL_HOURS],
            skip_date_normalization=True,  # Model data only needs day of week, not actual dates
            facility_col=FileColumns.MODEL_LOCATION_NAME,
            role_col=FileColumns.MODEL_STAFF_ROLE_NAME,
            employee_col=None  # Model data doesn't have employee IDs
        )
        
        # Combine all data quality exceptions from loaders and normalizers
        all_data_quality_exceptions = (
            facility_loader_exceptions + 
            model_loader_exceptions + 
            facility_data_quality_exceptions + 
            model_data_quality_exceptions
        )
        
        logger.info(f"Normalized data: {len(normalized_facility_df)} facility records, "
                   f"{len(normalized_model_df)} model records")
        logger.info(f"Total data quality issues captured: {len(all_data_quality_exceptions)}")
        logger.info(f"  Facility loader: {len(facility_loader_exceptions)}, Model loader: {len(model_loader_exceptions)}")
        logger.info(f"  Facility normalizer: {len(facility_data_quality_exceptions)}, Model normalizer: {len(model_data_quality_exceptions)}")
        
        # Display data quality summary if there are issues
        if all_data_quality_exceptions:
            display_data_quality_summary(all_data_quality_exceptions)
    
    # Step 3: Weekly Aggregation
    logger.info("Step 3: Weekly Aggregation")
    
    with TimedOperation(logger, "Weekly Aggregation"):
        weekly_facility_df = aggregate_to_weekly(normalized_facility_df)
        logger.info(f"Aggregated to {len(weekly_facility_df)} weekly records")
    
    # Step 4: Statistical Analysis
    logger.info("Step 4: Statistical Analysis")
    
    with TimedOperation(logger, "Descriptive Statistics Calculation"):
        statistics = calculate_facility_role_statistics(weekly_facility_df, normalized_model_df)
        logger.info(f"Calculated statistics for {len(statistics)} facility-role combinations")
    
    # Display statistics table (F-1a requirement for model data already handled in loader)
    display_statistics_table(statistics)
    
    # Step 5: Variance Detection
    logger.info("Step 5: Variance Detection")
    
    with TimedOperation(logger, "Variance Detection"):
        variances = detect_all_variances(
            normalized_facility_df,  # Use daily data for day-specific variance analysis
            normalized_model_df, 
            settings.control_variables
        )
        logger.info(f"Detected {len(variances)} variance exceptions")
    
    display_variance_summary(variances)
    
    # Step 6: Trend Analysis
    logger.info("Step 6: Trend Analysis")
    
    with TimedOperation(logger, "Trend Analysis"):
        trend_results = analyze_trends_for_all_facilities(
            normalized_facility_df,  # Use daily data for trend analysis which needs date information
            settings.control_variables
        )
        logger.info(f"Analyzed trends for {len(trend_results)} facility-role combinations")
    
    display_trend_summary(trend_results)
    
    # Step 7: Exception Compilation
    logger.info("Step 7: Exception Compilation")
    
    with TimedOperation(logger, "Exception Compilation"):
        exceptions_df = compile_exceptions(variances, trend_results)
        logger.info(f"Compiled {len(exceptions_df)} exceptions for reporting")
    
    display_exceptions_summary(exceptions_df)
    
    # Step 8: Export Results (if requested)
    if args.export_csv:
        logger.info("Step 8: Exporting Results to CSV")
        
        # Export exceptions
        exceptions_csv_path = os.path.join(args.output_dir, 'exceptions.csv')
        exceptions_df.to_csv(exceptions_csv_path, index=False)
        logger.info(f"Exported exceptions to {exceptions_csv_path}")
        
        # Export statistics summary
        from src.analysis.statistics import generate_statistics_summary_table
        stats_df = generate_statistics_summary_table(statistics)
        stats_csv_path = os.path.join(args.output_dir, 'statistics_summary.csv')
        stats_df.to_csv(stats_csv_path, index=False)
        logger.info(f"Exported statistics summary to {stats_csv_path}")
    
    # Step 9: PDF Report Generation (if not display-only)
    if not args.display_only:
        logger.info("Step 9: PDF Report Generation")
        
        # Check if PDF generation is available
        if check_pdf_generation_availability():
            logger.info("PDF generation available - generating facility reports")
            
            with TimedOperation(logger, "PDF Report Generation"):
                try:
                    # Generate comprehensive reports
                    report_results = asyncio.run(generate_comprehensive_reports(
                        settings=settings,
                        exceptions_df=exceptions_df,
                        facility_data=weekly_facility_df,
                        model_data=normalized_model_df,
                        statistics=statistics,
                        trend_results=trend_results,
                        analysis_start_date=weekly_facility_df['WeekStart'].min() if not weekly_facility_df.empty else datetime.now(),
                        analysis_end_date=weekly_facility_df['WeekStart'].max() if not weekly_facility_df.empty else datetime.now(),
                        data_quality_exceptions=all_data_quality_exceptions
                    ))
                    
                    if report_results['success']:
                        generated_reports = report_results['generated_reports']
                        logger.info(f"Successfully generated {len(generated_reports)} PDF reports")
                        logger.info(f"Reports saved to: {settings.directories.reports_dir}")
                        
                        # Display report generation summary
                        summary = report_results['summary']
                        logger.info(f"Report Generation Summary:")
                        logger.info(f"  - Facilities Processed: {summary['total_facilities_processed']}")
                        logger.info(f"  - Success Rate: {summary['success_rate']:.1f}%")
                        logger.info(f"  - Total Size: {summary['report_files']['total_size_mb']:.2f} MB")
                        
                        if summary.get('processing_errors'):
                            logger.warning("Some reports failed to generate - check logs for details")
                    else:
                        logger.error(f"PDF report generation failed: {report_results.get('error', 'Unknown error')}")
                        
                except Exception as e:
                    logger.error(f"Error during PDF report generation: {str(e)}")
                    logger.info("Analysis results are still available in console output and CSV exports")
        else:
            logger.warning("PDF generation not available (Playwright not installed)")
            logger.info("Install dependencies to enable PDF reports: pip install playwright matplotlib seaborn")
            logger.info("Analysis results are available in console output and CSV exports")
    
    # Final Summary
    logger.info("=" * 80)
    logger.info("ANALYSIS COMPLETE - SUMMARY")
    logger.info("=" * 80)
    
    # Overall statistics
    total_facilities = weekly_facility_df[FileColumns.FACILITY_LOCATION_NAME].nunique()
    total_roles = weekly_facility_df[FileColumns.FACILITY_STAFF_ROLE_NAME].nunique()
    facilities_with_exceptions = exceptions_df['facility'].nunique() if not exceptions_df.empty else 0
    
    logger.info(f"Facilities Analyzed: {total_facilities}")
    logger.info(f"Roles Analyzed: {total_roles}")
    logger.info(f"Total Exceptions: {len(exceptions_df)}")
    logger.info(f"Facilities with Exceptions: {facilities_with_exceptions}")
    
    if not exceptions_df.empty:
        exception_rate = (facilities_with_exceptions / total_facilities) * 100
        logger.info(f"Exception Rate: {exception_rate:.1f}%")
        
        # Exception breakdown
        model_exceptions = len(exceptions_df[exceptions_df['exception_type'] == 'model'])
        statistical_exceptions = len(exceptions_df[exceptions_df['exception_type'] == 'statistical'])
        trend_exceptions = len(exceptions_df[exceptions_df['exception_type'] == 'trend'])
        
        logger.info(f"Exception Breakdown:")
        logger.info(f"  Model Variances: {model_exceptions}")
        logger.info(f"  Statistical Exceptions: {statistical_exceptions}")
        logger.info(f"  Trend Exceptions: {trend_exceptions}")
    
    logger.info(f"Output Directory: {args.output_dir}")
    logger.info("=" * 80)
    
    # Exit with appropriate code
    if not exceptions_df.empty and facilities_with_exceptions > 0:
        logger.info(f"Analysis completed with {len(exceptions_df)} exceptions found")
        sys.exit(ExitCode.SUCCESS.value)  # Exceptions found is not an error, it's expected output
    else:
        logger.info("Analysis completed with no exceptions found")
        sys.exit(ExitCode.SUCCESS.value)


if __name__ == "__main__":
    main()