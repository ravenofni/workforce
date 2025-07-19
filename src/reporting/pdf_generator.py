"""
PDF Report Generator (F-6) - Generate facility PDF reports with Playwright.
Implements F-6a (cover page), F-6b (KPI summary), F-6c (charts), F-6d (exception details).
"""

import asyncio
import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape
import tempfile
import pandas as pd

from config.constants import (
    PDF_FORMAT, PDF_MARGIN_INCHES, DATE_FORMAT, FileColumns, ComparisonType,
    REPORT_SHOW_FACILITY_MODEL_ADHERENCE, REPORT_SHOW_VARIANCE_BY_DAY,
    REPORT_SHOW_UNMAPPED_HOURS, REPORT_SHOW_VISUAL_ANALYSIS,
    REPORT_SHOW_KPI_CHART, REPORT_SHOW_VARIANCE_HEATMAP,
    REPORT_SHOW_TREND_CHARTS, REPORT_SHOW_CONTROL_LIMITS_CHART,
    REPORT_SHOW_EXCEPTION_DETAILS, REPORT_SHOW_STATISTICAL_SUMMARY,
    REPORT_SHOW_TOP_VARIANCE_EMPLOYEES, REPORT_TOP_VARIANCE_EMPLOYEES_COUNT,
    REPORT_SHOW_TOP_UNMAPPED, REPORT_TOP_UNMAPPED_COUNT,
    REPORT_SHOW_TOP_VARIANCE_ROLES, REPORT_TOP_VARIANCE_ROLES_COUNT,
    REPORT_VARIANCE_FILTER, VarianceFilter,
    REPORT_SHOW_TOP_OVERTIME, REPORT_TOP_OVERTIME_COUNT, DISPLAY_UNMAPPED_TERM
)
from src.models.data_models import (
    StatisticalSummary,
    VarianceResult, 
    TrendAnalysisResult,
    ExceptionSummary,
    FacilityKPI
)
from src.utils.role_display_mapper import get_short_display_name, get_standard_display_name
from src.reporting.chart_generator import (
    create_variance_heatmap,
    create_trend_charts,
    create_kpi_summary_chart,
    create_control_limits_chart,
    cleanup_matplotlib
)
from src.reporting.exceptions import (
    filter_exceptions_by_facility,
    generate_facility_exception_summary,
    calculate_facility_kpis,
    calculate_period_model_hours
)
from src.utils.error_handlers import ReportGenerationError, handle_exceptions
from src.utils.weekday_converter import sunday_first_to_python_weekday
from src.analysis.unmapped_analysis import analyze_unmapped_hours_for_facility, format_unmapped_hours_for_display
from src.analysis.variance_employees_analysis import calculate_variance_employees_analysis
from src.analysis.top_unmapped_analysis import calculate_top_unmapped_analysis
from src.analysis.overtime_analysis import analyze_overtime, format_overtime_display


logger = logging.getLogger(__name__)

# Global variable to track Playwright availability
PLAYWRIGHT_AVAILABLE = False

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
    logger.info("Playwright successfully imported")
except ImportError:
    logger.warning("Playwright not available - PDF generation will be disabled")


class PDFReportGenerator:
    """
    PDF Report Generator implementing F-6 requirements.
    """
    
    def __init__(self, template_dir: str = None, output_dir: str = "output/reports", timeout_seconds: int = None):
        """
        Initialize PDF report generator.
        
        Args:
            template_dir: Directory containing HTML templates
            output_dir: Directory for generated PDF reports
            timeout_seconds: Timeout for PDF generation operations (from settings)
        """
        if template_dir is None:
            # Default to templates directory relative to this file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            template_dir = os.path.join(current_dir, "templates")
        
        self.template_dir = template_dir
        self.output_dir = output_dir
        
        # Use provided timeout or default from settings
        if timeout_seconds is not None:
            self.timeout = timeout_seconds * 1000  # Convert to milliseconds for Playwright
        else:
            from config.settings import get_settings
            settings = get_settings()
            self.timeout = settings.pdf_timeout_seconds * 1000
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(['html', 'xml'])
        )
        
        # Add custom filters
        self.jinja_env.filters['round'] = self._round_filter
        
        logger.info(f"PDF Report Generator initialized - Templates: {template_dir}, Output: {output_dir}")
    
    def _round_filter(self, value, precision=2):
        """Custom Jinja2 filter for rounding numbers."""
        try:
            return round(float(value), precision)
        except (ValueError, TypeError):
            return value
    
    def _generate_exception_management_table(self, facility_exceptions_df, 
                                           analysis_start_date: datetime, analysis_end_date: datetime) -> str:
        """
        Generate HTML table for exception management showing variances by role and day.
        
        Args:
            facility_exceptions_df: DataFrame with facility exceptions
            analysis_start_date: Start date of analysis
            analysis_end_date: End date of analysis
            
        Returns:
            HTML table string
        """
        if facility_exceptions_df.empty:
            return "<p>No model variance exceptions found for this period.</p>"
        
        # Filter for model variance exceptions only and within the analysis period
        model_exceptions = facility_exceptions_df[
            (facility_exceptions_df['exception_type'] == 'model') &
            (facility_exceptions_df['date'].dt.date >= analysis_start_date.date()) &
            (facility_exceptions_df['date'].dt.date <= analysis_end_date.date())
        ].copy()
        
        
        if model_exceptions.empty:
            return "<p>No model variance exceptions found for this period.</p>"
        
        # Always use day-of-week aggregation for weekly-oriented reports
        return self._generate_day_of_week_exception_table(model_exceptions, analysis_start_date, analysis_end_date)
    
    def _generate_day_of_week_exception_table(self, model_exceptions, _start_date: datetime, _end_date: datetime) -> str:
        """Generate day-of-week aggregated exception management table with manual page breaks."""
        # Get unique roles
        roles = sorted(model_exceptions['role'].unique())
        
        # Days of week in order starting with Sunday
        days_of_week = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
        
        # Configuration for page breaks - break table after this many rows
        MAX_ROWS_PER_PAGE = 16
        
        def create_table_header(is_continued=False):
            """Create table header HTML with optional continuation indicator."""
            continuation_text = " (continued)" if is_continued else ""
            header = '<table class="exception-management-table" style="width: 100%; max-width: 100%; table-layout: fixed; border-collapse: collapse; margin-bottom: 20px;">\n'
            header += '  <thead>\n    <tr>\n'
            header += f'      <th class="role-cell" style="width: 26%; border: 1px solid #bdc3c7; background-color: #f8f9fa; color: #2c3e50; padding: 8px 6px;">Role{continuation_text}</th>\n'
            
            # Each day gets equal width from remaining space (64% / 7 days ≈ 9% each)
            for day in days_of_week:
                header += f'      <th class="day-header" style="width: 9%; border: 1px solid #bdc3c7; background-color: #f8f9fa; color: #2c3e50; font-size: 9px; writing-mode: vertical-rl; text-orientation: mixed; padding: 8px 6px;">{day}</th>\n'
            
            # Add total column
            header += '      <th class="day-header" style="width: 10%; border: 1px solid #bdc3c7; background-color: #f8f9fa; color: #2c3e50; font-size: 9px; writing-mode: vertical-rl; text-orientation: mixed; padding: 8px 6px;">Total</th>\n'
            header += '    </tr>\n  </thead>\n  <tbody>\n'
            return header
        
        # Build table with manual page breaks
        complete_html = ""
        current_table_html = create_table_header(is_continued=False)
        rows_in_current_table = 0
        table_count = 0
        
        for role_index, role in enumerate(roles):
            # Check if we need to break the table
            if rows_in_current_table >= MAX_ROWS_PER_PAGE and role_index < len(roles) - 1:
                # Close current table properly with bottom border
                current_table_html += '  </tbody>\n</table>\n'
                complete_html += current_table_html
                # Add page break container
                complete_html += '<div style="page-break-before: always; margin-top: 20px;"></div>\n'
                # Start new table with continuation header
                current_table_html = create_table_header(is_continued=True)
                rows_in_current_table = 0
                table_count += 1
                
            role_exceptions = model_exceptions[model_exceptions['role'] == role]
            # Use short display name for the role
            try:
                display_role = get_short_display_name(role)
            except KeyError:
                display_role = role  # Fallback to original if mapping not found
            row_html = f'    <tr>\n      <td class="role-cell" style="word-wrap: break-word; overflow-wrap: break-word; padding: 2px 8px; border: 1px solid #bdc3c7; background-color: #2c3e50; color: white; font-weight: bold;">{display_role}</td>\n'
            
            # Collect daily variances and hours for average calculation
            daily_variances = []
            daily_hours = []
            
            # For each day of week, aggregate all instances across the analysis period
            for day_idx, _ in enumerate(days_of_week):
                # Convert our Sunday-first index to Python weekday format
                # day_idx: 0=Sun, 1=Mon, 2=Tue, ..., 6=Sat
                python_weekday = sunday_first_to_python_weekday(day_idx)
                
                # Filter exceptions for this day of week
                day_exceptions = role_exceptions[
                    role_exceptions['date'].dt.weekday == python_weekday
                ]
                
                if not day_exceptions.empty:
                    # Calculate sum of actual hours and model hours for this day
                    sum_actual_hours = day_exceptions['actual_hours'].sum()
                    sum_model_hours = day_exceptions['model_hours'].sum()
                    daily_hours.append(sum_actual_hours)
                    
                    # Calculate variance percentage based on sums
                    if sum_model_hours > 0:
                        day_variance = ((sum_actual_hours - sum_model_hours) / sum_model_hours) * 100
                    else:
                        day_variance = 999.0 if sum_actual_hours > 0 else 0.0
                    daily_variances.append(day_variance)
                    
                    # Handle special case of ±999% (zero model hours)
                    if abs(day_variance) >= 999:
                        # For infinite values, show hours with stop sign beneath and sign on left
                        inf_sign = "+" if day_variance >= 0 else "−"
                        
                        inf_cell_content = f'''
                        <div style="display: flex; align-items: center; justify-content: center; min-height: 25px;">
                            <span style="font-size: 12px; font-weight: bold; margin-right: 8px; color: #c62828;">{inf_sign}</span>
                            <div style="display: flex; flex-direction: column; align-items: center; line-height: 1.2;">
                                <div style="font-size: 10px; margin-bottom: 2px; font-family: monospace;">{sum_actual_hours:.1f}H</div>
                                <div style="font-size: 12px; text-align: center;">🛑</div>
                            </div>
                        </div>
                        '''
                        
                        row_html += f'      <td style="padding: 2px 12px; text-align: center; vertical-align: middle; border: 1px solid #bdc3c7;">{inf_cell_content}</td>\n'
                    else:
                        # No background color classes - using alternating row shading instead
                        
                        # Create flexbox layout with sign on left, values on right
                        sign = "+" if day_variance >= 0 else "−"
                        
                        cell_content = f'''
                        <div style="display: flex; align-items: center; justify-content: center; min-height: 25px;">
                            <span style="font-size: 11px; font-weight: bold; margin-right: 4px; color: #c62828;">{sign}</span>
                            <div style="display: flex; flex-direction: column; align-items: center; line-height: 1.1;">
                                <div style="font-size: 9px; margin-bottom: 1px; font-family: monospace;">{sum_actual_hours:.1f}H</div>
                                <div style="font-size: 9px; font-family: monospace;">{abs(day_variance):.0f}%</div>
                            </div>
                        </div>
                        '''
                        
                        row_html += f'      <td style="padding: 2px 12px; text-align: center; vertical-align: middle; border: 1px solid #bdc3c7;">{cell_content}</td>\n'
                else:
                    row_html += '      <td style="font-size: 14px; text-align: center; vertical-align: middle; padding: 2px 8px; border: 1px solid #bdc3c7;">✓</td>\n'
            
            # Calculate and add total column
            if daily_variances and daily_hours:
                overall_total_variance = sum(daily_variances) / len(daily_variances)  # Average variance across days
                overall_total_hours = sum(daily_hours)  # Total hours across all days
                
                # Handle special case of ±999% total
                if abs(overall_total_variance) >= 999:
                    # For infinite total values, show hours with stop sign beneath and sign on left
                    total_inf_sign = "+" if overall_total_variance >= 0 else "−"
                    
                    total_inf_cell_content = f'''
                    <div style="display: flex; align-items: center; justify-content: center; min-height: 25px;">
                        <span style="font-size: 12px; font-weight: bold; margin-right: 8px; color: #c62828;">{total_inf_sign}</span>
                        <div style="display: flex; flex-direction: column; align-items: center; line-height: 1.2;">
                            <div style="font-size: 10px; margin-bottom: 2px; font-family: monospace;">{overall_total_hours:.1f}H</div>
                            <div style="font-size: 12px; text-align: center;">🛑</div>
                        </div>
                    </div>
                    '''
                    
                    row_html += f'      <td style="padding: 2px 12px; text-align: center; vertical-align: middle; border: 1px solid #bdc3c7;">{total_inf_cell_content}</td>\n'
                else:
                    # No background color classes - using alternating row shading instead
                    
                    # Create flexbox layout for total column
                    total_sign = "+" if overall_total_variance >= 0 else "−"
                    
                    total_cell_content = f'''
                    <div style="display: flex; align-items: center; justify-content: center; min-height: 25px;">
                        <span style="font-size: 12px; font-weight: bold; margin-right: 8px; color: #c62828;">{total_sign}</span>
                        <div style="display: flex; flex-direction: column; align-items: center; line-height: 1.2;">
                            <div style="font-size: 10px; margin-bottom: 2px; font-family: monospace;">{overall_total_hours:.1f}H</div>
                            <div style="font-size: 10px; font-family: monospace;">{abs(overall_total_variance):.0f}%</div>
                        </div>
                    </div>
                    '''
                    
                    row_html += f'      <td style="padding: 2px 12px; text-align: center; vertical-align: middle; border: 1px solid #bdc3c7;">{total_cell_content}</td>\n'
            else:
                row_html += '      <td style="font-size: 14px; text-align: center; vertical-align: middle; padding: 2px 12px; border: 1px solid #bdc3c7;">✓</td>\n'
            
            row_html += '    </tr>\n'
            current_table_html += row_html
            rows_in_current_table += 1
        
        # Close final table
        current_table_html += '  </tbody>\n</table>\n'
        complete_html += current_table_html
        
        return complete_html
    
    async def generate_facility_report(self,
                                     facility: str,
                                     exceptions_df,
                                     facility_data,
                                     model_data,
                                     statistics: List[StatisticalSummary],
                                     trend_results: List[TrendAnalysisResult],
                                     analysis_start_date: datetime,
                                     analysis_end_date: datetime,
                                     daily_facility_data=None,
                                     comparison_type: ComparisonType = ComparisonType.TOTAL_STAFF) -> str:
        """
        Generate comprehensive PDF report for a facility (F-6 complete implementation).
        
        Args:
            facility: Facility name
            exceptions_df: DataFrame with compiled exceptions
            facility_data: DataFrame with facility hours data
            model_data: DataFrame with model hours data
            statistics: List of statistical summaries
            trend_results: List of trend analysis results
            analysis_start_date: Start date of analysis period
            analysis_end_date: End date of analysis period
            daily_facility_data: Optional daily facility data for trend charts
            comparison_type: Type of comparison for model calculations (TOTAL_STAFF or PER_PERSON)
            
        Returns:
            Path to generated PDF file
            
        Raises:
            ReportGenerationError: If PDF generation fails
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise ReportGenerationError(
                "PDF generation not available - Playwright not installed",
                facility=facility
            )
        
        logger.info(f"Starting PDF report generation for {facility}")
        
        try:
            # Prepare report data
            report_data = await self._prepare_report_data(
                facility, exceptions_df, facility_data, model_data,
                statistics, trend_results, analysis_start_date, analysis_end_date,
                daily_facility_data, comparison_type
            )
            
            # Generate HTML content
            html_content = self._render_html_template(report_data)
            
            # Convert to PDF
            pdf_path = await self._convert_html_to_pdf(facility, html_content)
            
            # Report metadata could be created here if needed for future enhancements
            
            logger.info(f"Successfully generated PDF report for {facility}: {pdf_path}")
            return pdf_path
            
        except Exception as e:
            logger.error(f"Error generating PDF report for {facility}: {str(e)}")
            raise ReportGenerationError(
                f"Failed to generate PDF report: {str(e)}",
                facility=facility
            ) from e
        finally:
            # Clean up matplotlib resources
            cleanup_matplotlib()
    
    async def _prepare_report_data(self,
                                  facility: str,
                                  exceptions_df,
                                  facility_data,
                                  model_data,
                                  statistics: List[StatisticalSummary],
                                  trend_results: List[TrendAnalysisResult],
                                  analysis_start_date: datetime,
                                  analysis_end_date: datetime,
                                  daily_facility_data=None,
                                  comparison_type: ComparisonType = ComparisonType.TOTAL_STAFF) -> Dict[str, Any]:
        """
        Prepare all data needed for report generation.
        
        Args:
            facility: Facility name
            exceptions_df: DataFrame with exceptions
            facility_data: DataFrame with facility data
            model_data: DataFrame with model data
            statistics: Statistical summaries
            trend_results: Trend analysis results
            analysis_start_date: Analysis start date
            analysis_end_date: Analysis end date
            daily_facility_data: Optional daily facility data for trend charts
            comparison_type: Type of comparison for model calculations
            
        Returns:
            Dictionary with all report data
        """
        logger.debug(f"Preparing report data for {facility}")
        
        # Filter data for this facility
        facility_exceptions = filter_exceptions_by_facility(exceptions_df, facility)
        facility_statistics = [s for s in statistics if s.facility == facility]
        facility_trends = [t for t in trend_results if t.facility == facility]
        
        # Generate exception summary
        exception_summary = generate_facility_exception_summary(exceptions_df, facility)
        
        # Calculate KPIs with comparison type
        kpis = calculate_facility_kpis(
            exceptions_df, facility_data, model_data, facility,
            analysis_start_date, analysis_end_date, comparison_type
        )
        
        # Generate charts
        logger.debug(f"Generating charts for {facility}")
        
        # F-6b: KPI summary chart
        kpi_chart = create_kpi_summary_chart(kpis)
        
        # F-6c: Variance heat-map
        variance_heatmap = None
        if not facility_exceptions.empty:
            variance_heatmap = create_variance_heatmap(exceptions_df, facility)
        
        # F-6c: Trend charts
        trend_charts = None
        if facility_trends:
            # Use daily facility data for trend charts if available, otherwise fallback to facility_data
            trend_data = daily_facility_data if daily_facility_data is not None else facility_data
            trend_charts = create_trend_charts(trend_data, facility_trends, facility)
        
        # Control limits chart
        control_limits_chart = None
        if facility_statistics:
            control_limits_chart = create_control_limits_chart(facility_statistics, facility)
        
        # Prepare exceptions list for detailed display with pagination
        exceptions_list = []
        exceptions_pagination = {}
        if not facility_exceptions.empty:
            from config.settings import get_settings
            settings = get_settings()
            max_per_page = settings.max_exceptions_per_page
            max_summary = settings.max_exceptions_summary
            
            all_exceptions = facility_exceptions.to_dict('records')
            
            # For summary display (limited count)
            exceptions_list = all_exceptions[:max_summary]
            
            # For pagination info
            total_exceptions = len(all_exceptions)
            total_pages = (total_exceptions + max_per_page - 1) // max_per_page  # Ceiling division
            
            exceptions_pagination = {
                'total_exceptions': total_exceptions,
                'total_pages': total_pages,
                'max_per_page': max_per_page,
                'showing_summary': total_exceptions > max_summary,
                'truncated_count': max(0, total_exceptions - max_summary)
            }
        
        # Generate exception management table
        exception_management_table = self._generate_exception_management_table(
            facility_exceptions, analysis_start_date, analysis_end_date
        )
        
        # Calculate top 3 problematic roles by total hours deviation (for analysis period only)
        variance_roles_data, variance_summary_stats = self._calculate_period_variance_by_role(
            facility, facility_data, model_data, analysis_start_date, analysis_end_date, comparison_type
        )
        
        # Analyze unmapped hours for this facility using daily data
        logger.debug(f"Analyzing unmapped hours for {facility}")
        try:
            # Use daily_facility_data if available (has employee details), otherwise fall back to facility_data
            data_for_unmapped = daily_facility_data if daily_facility_data is not None else facility_data
            
            unmapped_results, category_summaries = analyze_unmapped_hours_for_facility(
                data_for_unmapped, facility, analysis_start_date, analysis_end_date
            )
            unmapped_hours_data = format_unmapped_hours_for_display(unmapped_results, category_summaries)
            
            if unmapped_hours_data['has_unmapped_hours']:
                logger.info(f"Found {unmapped_hours_data['total_unmapped_hours']} unmapped hours across {unmapped_hours_data['total_categories']} categories for {facility}")
            else:
                logger.info(f"No unmapped hours found for {facility}")
                
        except Exception as e:
            logger.warning(f"Failed to analyze unmapped hours for {facility}: {str(e)}")
            unmapped_hours_data = {
                'has_unmapped_hours': False,
                'total_unmapped_hours': 0,
                'total_categories': 0,
                'total_employees': 0,
                'categories': [],
                'detailed_results': []
            }
        
        # Analyze overtime for this facility
        logger.debug(f"Analyzing overtime for {facility}")
        try:
            # Use daily facility data for overtime analysis (need individual daily records)
            data_for_overtime = daily_facility_data if daily_facility_data is not None else facility_data
            
            # Debug: Check what facilities are in the data
            if not data_for_overtime.empty and FileColumns.FACILITY_LOCATION_NAME in data_for_overtime.columns:
                unique_facilities = data_for_overtime[FileColumns.FACILITY_LOCATION_NAME].unique()
                logger.debug(f"Available facilities in overtime data: {unique_facilities}")
                logger.debug(f"Looking for facility: '{facility}'")
                logger.debug(f"Using {'daily' if daily_facility_data is not None else 'weekly'} data for overtime analysis")
            
            # Filter facility data for this specific facility
            if FileColumns.FACILITY_LOCATION_NAME in data_for_overtime.columns:
                facility_df = data_for_overtime[data_for_overtime[FileColumns.FACILITY_LOCATION_NAME] == facility].copy()
            else:
                logger.warning(f"FACILITY_LOCATION_NAME column not found in overtime data. Available columns: {list(data_for_overtime.columns)}")
                facility_df = pd.DataFrame()
            logger.debug(f"Filtered overtime data shape: {facility_df.shape}")
            
            variance_employees_analysis = calculate_variance_employees_analysis(
                facility_df=facility_df,
                facility_name=facility,
                analysis_start_date=analysis_start_date,
                analysis_end_date=analysis_end_date,
                top_count=REPORT_TOP_VARIANCE_EMPLOYEES_COUNT,
                model_data=model_data
            )
            
            if variance_employees_analysis.total_employees_with_variance > 0:
                logger.info(f"Found {variance_employees_analysis.total_employees_with_variance} employees with variance "
                           f"({variance_employees_analysis.total_variance_hours_facility:.2f} total hours) for {facility}")
            else:
                logger.info(f"No variance employees found for {facility}")
                
        except Exception as e:
            logger.warning(f"Failed to analyze variance employees for {facility}: {str(e)}")
            from src.models.data_models import VarianceEmployeesAnalysis
            variance_employees_analysis = VarianceEmployeesAnalysis(
                facility=facility,
                top_employees=[],
                total_employees_with_variance=0,
                top_count_requested=REPORT_TOP_VARIANCE_EMPLOYEES_COUNT,
                total_variance_hours_facility=0.0,
                analysis_period_start=analysis_start_date,
                analysis_period_end=analysis_end_date
            )
        
        # Analyze top unmapped hours for this facility
        logger.debug(f"Analyzing top unmapped hours for {facility}")
        try:
            # Use daily facility data for unmapped analysis (need individual daily records)
            data_for_unmapped_top = daily_facility_data if daily_facility_data is not None else facility_data
            
            # Filter facility data for this specific facility
            if FileColumns.FACILITY_LOCATION_NAME in data_for_unmapped_top.columns:
                facility_df_unmapped = data_for_unmapped_top[data_for_unmapped_top[FileColumns.FACILITY_LOCATION_NAME] == facility].copy()
            else:
                logger.warning(f"FACILITY_LOCATION_NAME column not found in unmapped data. Available columns: {list(data_for_unmapped_top.columns)}")
                facility_df_unmapped = pd.DataFrame()
            logger.debug(f"Filtered unmapped data shape: {facility_df_unmapped.shape}")
            
            top_unmapped_analysis = calculate_top_unmapped_analysis(
                facility_df=facility_df_unmapped,
                facility_name=facility,
                analysis_start_date=analysis_start_date,
                analysis_end_date=analysis_end_date,
                top_count=REPORT_TOP_UNMAPPED_COUNT
            )
            
            if top_unmapped_analysis.total_employees_with_unmapped > 0:
                logger.info(f"Found {top_unmapped_analysis.total_employees_with_unmapped} employees with unmapped hours "
                           f"({top_unmapped_analysis.total_unmapped_hours_facility:.2f} total hours) for {facility}")
            else:
                logger.info(f"No unmapped hours found for {facility}")
                
        except Exception as e:
            logger.warning(f"Failed to analyze top unmapped hours for {facility}: {str(e)}")
            from src.models.data_models import TopUnmappedAnalysis
            top_unmapped_analysis = TopUnmappedAnalysis(
                facility=facility,
                top_employees=[],
                total_employees_with_unmapped=0,
                top_count_requested=REPORT_TOP_UNMAPPED_COUNT,
                total_unmapped_hours_facility=0.0,
                analysis_period_start=analysis_start_date,
                analysis_period_end=analysis_end_date
            )
        
        # Analyze overtime for this facility
        logger.debug(f"Analyzing overtime for {facility}")
        overtime_analysis = None
        try:
            # Use daily facility data for overtime analysis (need individual employee records)
            data_for_overtime = daily_facility_data if daily_facility_data is not None else facility_data
            
            # Filter facility data for this specific facility
            if FileColumns.FACILITY_LOCATION_NAME in data_for_overtime.columns:
                facility_df_overtime = data_for_overtime[data_for_overtime[FileColumns.FACILITY_LOCATION_NAME] == facility].copy()
            else:
                logger.warning(f"FACILITY_LOCATION_NAME column not found in overtime data")
                facility_df_overtime = pd.DataFrame()
            
            if not facility_df_overtime.empty:
                # Prepare data for overtime analysis
                overtime_df = pd.DataFrame({
                    'employee_id': facility_df_overtime[FileColumns.FACILITY_EMPLOYEE_ID] if FileColumns.FACILITY_EMPLOYEE_ID in facility_df_overtime.columns else '',
                    'employee_name': facility_df_overtime[FileColumns.FACILITY_EMPLOYEE_NAME] if FileColumns.FACILITY_EMPLOYEE_NAME in facility_df_overtime.columns else '',
                    'actual_hours': facility_df_overtime[FileColumns.FACILITY_TOTAL_HOURS],
                    'role': facility_df_overtime[FileColumns.FACILITY_STAFF_ROLE_NAME],
                    'date': pd.to_datetime(facility_df_overtime[FileColumns.FACILITY_HOURS_DATE]) if FileColumns.FACILITY_HOURS_DATE in facility_df_overtime.columns else analysis_start_date,
                    'week_start': analysis_start_date  # Will be properly set in the analysis function
                })
                
                overtime_result = analyze_overtime(
                    facility_df=overtime_df,
                    facility=facility,
                    week_start_date=analysis_start_date,
                    week_end_date=analysis_end_date
                )
                overtime_analysis = format_overtime_display(overtime_result)
                
                if overtime_result.employee_count > 0:
                    logger.info(f"Found {overtime_result.employee_count} employees with "
                               f"{overtime_result.total_overtime_hours:.1f} total overtime hours for {facility}")
                else:
                    logger.info(f"No overtime found for {facility}")
            else:
                logger.info(f"No data available for overtime analysis for {facility}")
                
        except Exception as e:
            logger.warning(f"Failed to analyze overtime for {facility}: {str(e)}", exc_info=True)
            overtime_analysis = None
        
        return {
            'facility_name': facility,
            'analysis_start_date': analysis_start_date.strftime(DATE_FORMAT),
            'analysis_end_date': analysis_end_date.strftime(DATE_FORMAT),
            'generation_date': datetime.now().strftime(f"{DATE_FORMAT} %H:%M:%S"),
            'summary': exception_summary,
            'kpis': kpis,
            'exceptions_list': exceptions_list,
            'exceptions_pagination': exceptions_pagination,
            'exception_management_table': exception_management_table,
            'statistics_summary': facility_statistics,
            'kpi_chart': kpi_chart,
            'variance_heatmap': variance_heatmap,
            'trend_charts': trend_charts,
            'control_limits_chart': control_limits_chart,
            'control_variables': {
                'analysis_period_days': (analysis_end_date - analysis_start_date).days,
                'total_exceptions': len(exceptions_list),
                'roles_analyzed': len(facility_statistics)
            },
            'total_data_points': len(facility_data[facility_data[FileColumns.FACILITY_LOCATION_NAME] == facility]) if not facility_data.empty and FileColumns.FACILITY_LOCATION_NAME in facility_data.columns else 0,
            'variance_roles_data': variance_roles_data,
            'variance_summary_stats': variance_summary_stats,
            'unmapped_hours': unmapped_hours_data,
            'variance_employees_analysis': variance_employees_analysis,
            'top_unmapped_analysis': top_unmapped_analysis,
            'overtime_analysis': overtime_analysis,
            # Report display controls
            'show_facility_model_adherence': REPORT_SHOW_FACILITY_MODEL_ADHERENCE,
            'show_variance_by_day': REPORT_SHOW_VARIANCE_BY_DAY,
            'show_unmapped_hours': REPORT_SHOW_UNMAPPED_HOURS,
            'show_visual_analysis': REPORT_SHOW_VISUAL_ANALYSIS,
            'show_kpi_chart': REPORT_SHOW_KPI_CHART,
            'show_variance_heatmap': REPORT_SHOW_VARIANCE_HEATMAP,
            'show_trend_charts': REPORT_SHOW_TREND_CHARTS,
            'show_control_limits_chart': REPORT_SHOW_CONTROL_LIMITS_CHART,
            'show_exception_details': REPORT_SHOW_EXCEPTION_DETAILS,
            'show_statistical_summary': REPORT_SHOW_STATISTICAL_SUMMARY,
            'show_top_variance_employees': REPORT_SHOW_TOP_VARIANCE_EMPLOYEES,
            'show_top_unmapped': REPORT_SHOW_TOP_UNMAPPED,
            'show_top_variance_roles': REPORT_SHOW_TOP_VARIANCE_ROLES,
            'show_top_overtime': REPORT_SHOW_TOP_OVERTIME,
            # Count configuration values
            'top_variance_roles_count': REPORT_TOP_VARIANCE_ROLES_COUNT,
            'top_variance_employees_count': REPORT_TOP_VARIANCE_EMPLOYEES_COUNT,
            'top_unmapped_count': REPORT_TOP_UNMAPPED_COUNT,
            'top_overtime_count': REPORT_TOP_OVERTIME_COUNT,
            # Display terminology
            'display_unmapped_term': DISPLAY_UNMAPPED_TERM.lower(),
            'display_unmapped_term_title': DISPLAY_UNMAPPED_TERM
        }
    
    def _render_html_template(self, report_data: Dict[str, Any]) -> str:
        """
        Render HTML template with report data.
        
        Args:
            report_data: Dictionary with report data
            
        Returns:
            Rendered HTML content
        """
        try:
            template = self.jinja_env.get_template('facility_report.html')
            html_content = template.render(**report_data)
            
            logger.debug(f"Successfully rendered HTML template for {report_data['facility_name']}")
            return html_content
            
        except Exception as e:
            logger.error(f"Error rendering HTML template: {str(e)}")
            raise ReportGenerationError(f"Template rendering failed: {str(e)}")
    
    def _calculate_period_variance_by_role(self, facility: str, facility_data: pd.DataFrame, 
                                         model_data: pd.DataFrame, analysis_start_date: datetime, 
                                         analysis_end_date: datetime,
                                         comparison_type: ComparisonType = ComparisonType.TOTAL_STAFF) -> tuple:
        """
        Calculate top 3 variance roles by comparing actual vs model hours for the analysis period only.
        
        Args:
            facility: Facility name
            facility_data: DataFrame with facility data
            model_data: DataFrame with model data
            analysis_start_date: Start date of analysis period
            analysis_end_date: End date of analysis period
            comparison_type: Type of comparison (TOTAL_STAFF or PER_PERSON)
            
        Returns:
            Tuple of (top_roles_list, summary_stats_dict) where:
            - top_roles_list: List of formatted variance strings for top 3 roles
            - summary_stats_dict: Dict with 'total_variance_hours' and 'roles_with_variances'
        """
        top_problem_roles = []
        summary_stats = {'total_variance_hours': 0.0, 'roles_with_variances': 0}
        
        # Check if we have the required columns for period-based calculation
        # Note: facility_data is weekly aggregated data, so it doesn't have FACILITY_HOURS_DATE
        required_facility_cols = [FileColumns.FACILITY_LOCATION_NAME, 
                                FileColumns.FACILITY_STAFF_ROLE_NAME, FileColumns.FACILITY_TOTAL_HOURS]
        required_model_cols = [FileColumns.MODEL_LOCATION_NAME, FileColumns.MODEL_STAFF_ROLE_NAME,
                             FileColumns.MODEL_TOTAL_HOURS, FileColumns.MODEL_DAY_NUMBER]
        
        # Check facility data columns
        if facility_data.empty or not all(col in facility_data.columns for col in required_facility_cols):
            logger.warning(f"Cannot calculate period variance: missing facility data columns. Available: {list(facility_data.columns) if not facility_data.empty else 'empty'}")
            return top_problem_roles, summary_stats
            
        # Check model data columns  
        if model_data.empty or not all(col in model_data.columns for col in required_model_cols):
            logger.warning(f"Cannot calculate period variance: missing model data columns. Available: {list(model_data.columns) if not model_data.empty else 'empty'}")
            return top_problem_roles, summary_stats
        
        try:
            # Filter facility data for this facility only (like KPI calculation - no date filtering)
            # The facility_data should already be filtered to the analysis period by the caller
            facility_hours = facility_data[facility_data[FileColumns.FACILITY_LOCATION_NAME] == facility]
            
            logger.debug(f"Facility {facility} data shape: {facility_hours.shape}")
            
            if facility_hours.empty:
                logger.debug(f"No facility data found for {facility}")
                return top_problem_roles, summary_stats
            
            # Get actual hours by role for the analysis period (data is already aggregated weekly)
            role_actual_hours = facility_hours.groupby(FileColumns.FACILITY_STAFF_ROLE_NAME)[FileColumns.FACILITY_TOTAL_HOURS].sum()
            
            logger.debug(f"Actual hours by role for {facility}: {dict(role_actual_hours)}")
            
            # Use the ModelDataService for enhanced model data handling
            from src.services.model_data_service import ModelDataService
            model_service = ModelDataService(model_data)
            
            # Get total model hours for validation
            total_model_hours = calculate_period_model_hours(
                model_data, facility, analysis_start_date, analysis_end_date, comparison_type
            )
            
            logger.debug(f"Total model hours for {facility} ({comparison_type.value}): {total_model_hours}")
            
            # Calculate model hours by role for the analysis period using the service
            role_model_hours = {}
            
            # Get all roles for this facility
            facility_roles = model_service.get_facility_role_standards(facility)
            
            if not facility_roles:
                logger.debug(f"No model data found for {facility}")
                return top_problem_roles, summary_stats
            
            # Calculate period model hours for each role efficiently
            period_days = (analysis_end_date - analysis_start_date).days + 1
            
            for role in facility_roles.keys():
                try:
                    role_standards = facility_roles[role]
                    if comparison_type == ComparisonType.TOTAL_STAFF:
                        # Total staff: daily hours per role × staff count × number of days
                        daily_total = role_standards['daily_hours_per_role'] * role_standards['staff_count']
                    else:  # PER_PERSON
                        # Per person: daily hours per role × number of days
                        daily_total = role_standards['daily_hours_per_role']
                    
                    role_model_hours[role] = daily_total * period_days
                    
                except Exception as e:
                    logger.warning(f"Error calculating period hours for role {role}: {e}")
                    role_model_hours[role] = 0.0
            
            logger.debug(f"Calculated model hours by role for {facility} ({comparison_type.value}): {role_model_hours}")
            
            # Calculate variance for each role that has actual hours
            role_variances = []
            for role in role_actual_hours.index:
                actual_hours = role_actual_hours[role]
                model_hours = role_model_hours.get(role, 0.0)
                
                # Calculate signed deviation (positive = above model, negative = below model)
                signed_deviation = actual_hours - model_hours
                abs_deviation = abs(signed_deviation)
                
                role_variances.append({
                    'role': role,
                    'actual_hours': actual_hours,
                    'model_hours': model_hours,
                    'signed_deviation': signed_deviation,
                    'abs_deviation': abs_deviation
                })
            
            # Apply variance filter based on configuration
            if REPORT_VARIANCE_FILTER == VarianceFilter.ABOVE_MODEL:
                role_variances = [v for v in role_variances if v['signed_deviation'] > 0]
                logger.debug(f"Filtered to above model variances: {len(role_variances)} roles")
            elif REPORT_VARIANCE_FILTER == VarianceFilter.BELOW_MODEL:
                role_variances = [v for v in role_variances if v['signed_deviation'] < 0]
                logger.debug(f"Filtered to below model variances: {len(role_variances)} roles")
            # For VarianceFilter.ALL, no filtering is applied
            
            # Sort by absolute deviation and get top N
            role_variances.sort(key=lambda x: x['abs_deviation'], reverse=True)
            
            logger.debug(f"Top role variances for {facility}: {role_variances[:REPORT_TOP_VARIANCE_ROLES_COUNT]}")
            
            # Calculate summary statistics
            total_variance_hours = sum(variance['abs_deviation'] for variance in role_variances)
            roles_with_variances = len([v for v in role_variances if v['abs_deviation'] > 0])
            
            summary_stats = {
                'total_variance_hours': total_variance_hours,
                'roles_with_variances': roles_with_variances
            }
            
            # Separate roles by function (clinical vs non-clinical) like variance employees
            from src.utils.role_display_mapper import get_role_function, get_standard_display_name
            
            clinical_roles = []
            non_clinical_roles = []
            
            for variance in role_variances:
                try:
                    # Get function classification for this role
                    role_function = get_role_function(variance['role'])
                    
                    # Get display name
                    try:
                        display_role = get_standard_display_name(variance['role'])
                    except KeyError:
                        display_role = variance['role']  # Fallback to original if mapping not found
                    
                    # Format with sign and impact
                    sign = "+" if variance['signed_deviation'] >= 0 else ""
                    formatted_role = f"{display_role}|{sign}{variance['signed_deviation']:.0f}"
                    
                    # Group by function
                    if role_function == "clinical":
                        clinical_roles.append(formatted_role)
                    else:
                        non_clinical_roles.append(formatted_role)
                        
                except KeyError:
                    logger.warning(f"No function found for role '{variance['role']}', defaulting to non-clinical")
                    # Default to non-clinical for unmapped roles
                    try:
                        display_role = get_standard_display_name(variance['role'])
                    except KeyError:
                        display_role = variance['role']
                    
                    sign = "+" if variance['signed_deviation'] >= 0 else ""
                    formatted_role = f"{display_role}|{sign}{variance['signed_deviation']:.0f}"
                    non_clinical_roles.append(formatted_role)
                except Exception as e:
                    logger.error(f"Error processing role '{variance['role']}': {str(e)}")
                    continue
            
            # Create the grouped data structure
            variance_roles_data = {
                'clinical_roles': clinical_roles[:REPORT_TOP_VARIANCE_ROLES_COUNT],
                'non_clinical_roles': non_clinical_roles[:REPORT_TOP_VARIANCE_ROLES_COUNT],
                'total_variance_hours': total_variance_hours,
                'roles_with_variances': roles_with_variances
            }
            
            # For backward compatibility, also create the legacy flat list
            all_roles_limited = clinical_roles[:REPORT_TOP_VARIANCE_ROLES_COUNT] + non_clinical_roles[:REPORT_TOP_VARIANCE_ROLES_COUNT]
            top_problem_roles = all_roles_limited[:REPORT_TOP_VARIANCE_ROLES_COUNT]
                
            logger.debug(f"Clinical roles: {clinical_roles[:REPORT_TOP_VARIANCE_ROLES_COUNT]}")
            logger.debug(f"Non-clinical roles: {non_clinical_roles[:REPORT_TOP_VARIANCE_ROLES_COUNT]}")
            logger.debug(f"Legacy top_problem_roles: {top_problem_roles}")
            logger.debug(f"Summary stats: {summary_stats}")
            
        except Exception as e:
            logger.error(f"Error calculating period variance by role for {facility}: {str(e)}")
            logger.debug(f"Facility data shape: {facility_data.shape}, Model data shape: {model_data.shape}")
            variance_roles_data = {'clinical_roles': [], 'non_clinical_roles': [], 'total_variance_hours': 0.0, 'roles_with_variances': 0}
        
        return variance_roles_data, summary_stats
    
    async def _convert_html_to_pdf(self, facility: str, html_content: str) -> str:
        """
        Convert HTML content to PDF using Playwright.
        
        Args:
            facility: Facility name for filename
            html_content: HTML content to convert
            
        Returns:
            Path to generated PDF file
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise ReportGenerationError("Playwright not available for PDF conversion")
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{facility.replace(' ', '_')}_{timestamp}.pdf"
        pdf_path = os.path.join(self.output_dir, filename)
        
        async with async_playwright() as playwright:
            try:
                logger.debug(f"Launching browser for PDF conversion: {facility}")
                
                # Launch browser with appropriate settings
                browser = await playwright.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox', 
                        '--disable-dev-shm-usage',
                        '--disable-accelerated-2d-canvas',
                        '--disable-gpu'
                    ]
                )
                
                # Create browser context with viewport
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080}
                )
                
                page = await context.new_page()
                
                # Set content and wait for page to fully load
                await page.set_content(html_content, wait_until='networkidle')
                
                # Wait a bit more for any dynamic content and fonts to load
                await page.wait_for_timeout(2000)
                
                # Generate PDF with proper settings
                await page.pdf(
                    path=pdf_path,
                    format=PDF_FORMAT,
                    margin={
                        'top': f'{PDF_MARGIN_INCHES}in',
                        'bottom': f'{PDF_MARGIN_INCHES}in',
                        'left': f'{PDF_MARGIN_INCHES}in',
                        'right': f'{PDF_MARGIN_INCHES}in'
                    },
                    print_background=True,
                    prefer_css_page_size=True
                )
                
                logger.debug(f"PDF generated successfully: {pdf_path}")
                await browser.close()
                return pdf_path
                
            except Exception as e:
                logger.error(f"Error converting HTML to PDF for {facility}: {str(e)}")
                raise ReportGenerationError(f"PDF conversion failed: {str(e)}", facility=facility) from e
    
    async def generate_multiple_facility_reports(self,
                                                facilities: List[str],
                                                exceptions_df,
                                                facility_data,
                                                model_data,
                                                statistics: List[StatisticalSummary],
                                                trend_results: List[TrendAnalysisResult],
                                                analysis_start_date: datetime,
                                                analysis_end_date: datetime,
                                                exceptions_only: bool = False) -> List[str]:
        """
        Generate PDF reports for multiple facilities.
        
        Args:
            facilities: List of facility names
            exceptions_df: DataFrame with exceptions
            facility_data: DataFrame with facility data
            model_data: DataFrame with model data
            statistics: Statistical summaries
            trend_results: Trend analysis results
            analysis_start_date: Analysis start date
            analysis_end_date: Analysis end date
            exceptions_only: Only generate reports for facilities with exceptions
            
        Returns:
            List of paths to generated PDF files
        """
        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("Playwright not available - skipping PDF generation")
            return []
        
        generated_reports = []
        
        logger.info(f"Generating PDF reports for {len(facilities)} facilities")
        
        for facility in facilities:
            try:
                # Check if facility has exceptions (if exceptions_only mode)
                if exceptions_only:
                    facility_exceptions = filter_exceptions_by_facility(exceptions_df, facility)
                    if facility_exceptions.empty:
                        logger.info(f"Skipping {facility} - no exceptions found (exceptions-only mode)")
                        continue
                
                # Generate report for this facility
                pdf_path = await self.generate_facility_report(
                    facility, exceptions_df, facility_data, model_data,
                    statistics, trend_results, analysis_start_date, analysis_end_date
                )
                
                generated_reports.append(pdf_path)
                logger.info(f"Generated report {len(generated_reports)}/{len(facilities)}: {facility}")
                
            except Exception as e:
                logger.error(f"Failed to generate report for {facility}: {str(e)}")
                continue
        
        logger.info(f"Successfully generated {len(generated_reports)} PDF reports")
        return generated_reports
    
    def get_report_summary(self, generated_reports: List[str]) -> Dict[str, Any]:
        """
        Get summary information about generated reports.
        
        Args:
            generated_reports: List of generated report file paths
            
        Returns:
            Dictionary with summary information
        """
        total_size = 0
        report_info = []
        
        for report_path in generated_reports:
            if os.path.exists(report_path):
                size = os.path.getsize(report_path)
                total_size += size
                
                facility_name = os.path.basename(report_path).split('_')[0]
                report_info.append({
                    'facility': facility_name,
                    'file_path': report_path,
                    'file_size_mb': size / (1024 * 1024),
                    'generated_at': datetime.fromtimestamp(os.path.getctime(report_path))
                })
        
        return {
            'total_reports': len(generated_reports),
            'total_size_mb': total_size / (1024 * 1024),
            'output_directory': self.output_dir,
            'reports': report_info
        }


@handle_exceptions(exit_on_error=False)
async def generate_facility_pdf_report(facility: str,
                                     exceptions_df,
                                     facility_data,
                                     model_data,
                                     statistics: List[StatisticalSummary],
                                     trend_results: List[TrendAnalysisResult],
                                     analysis_start_date: datetime,
                                     analysis_end_date: datetime,
                                     output_dir: str = "output/reports") -> Optional[str]:
    """
    Convenience function to generate a single facility PDF report.
    
    Args:
        facility: Facility name
        exceptions_df: DataFrame with exceptions
        facility_data: DataFrame with facility data  
        model_data: DataFrame with model data
        statistics: Statistical summaries
        trend_results: Trend analysis results
        analysis_start_date: Analysis start date
        analysis_end_date: Analysis end date
        output_dir: Output directory for PDF
        
    Returns:
        Path to generated PDF file or None if failed
    """
    generator = PDFReportGenerator(output_dir=output_dir)
    
    try:
        return await generator.generate_facility_report(
            facility, exceptions_df, facility_data, model_data,
            statistics, trend_results, analysis_start_date, analysis_end_date
        )
    except Exception as e:
        logger.error(f"Failed to generate PDF report for {facility}: {str(e)}")
        return None


def check_pdf_generation_availability() -> bool:
    """
    Check if PDF generation is available.
    
    Returns:
        True if Playwright is available, False otherwise
    """
    return PLAYWRIGHT_AVAILABLE