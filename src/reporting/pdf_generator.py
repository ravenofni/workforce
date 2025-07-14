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

from config.constants import PDF_FORMAT, PDF_MARGIN_INCHES, DATE_FORMAT, FileColumns
from src.models.data_models import (
    StatisticalSummary,
    VarianceResult, 
    TrendAnalysisResult,
    ExceptionSummary,
    FacilityKPI,
    ReportMetadata
)
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
    calculate_facility_kpis
)
from src.utils.error_handlers import ReportGenerationError, handle_exceptions


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
    
    async def generate_facility_report(self,
                                     facility: str,
                                     exceptions_df,
                                     facility_data,
                                     model_data,
                                     statistics: List[StatisticalSummary],
                                     trend_results: List[TrendAnalysisResult],
                                     analysis_start_date: datetime,
                                     analysis_end_date: datetime,
                                     daily_facility_data=None) -> str:
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
                daily_facility_data
            )
            
            # Generate HTML content
            html_content = self._render_html_template(report_data)
            
            # Convert to PDF
            pdf_path = await self._convert_html_to_pdf(facility, html_content)
            
            # Create report metadata
            metadata = ReportMetadata(
                facility=facility,
                generated_at=datetime.now(),
                analysis_period_start=analysis_start_date,
                analysis_period_end=analysis_end_date,
                control_variables_used=report_data['control_variables'],
                total_data_points=report_data['total_data_points'],
                has_exceptions=report_data['summary'].total_exceptions > 0,
                report_file_path=pdf_path
            )
            
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
                                  daily_facility_data=None) -> Dict[str, Any]:
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
        
        # Calculate KPIs
        kpis = calculate_facility_kpis(
            exceptions_df, facility_data, model_data, facility
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
        
        return {
            'facility_name': facility,
            'analysis_start_date': analysis_start_date.strftime(DATE_FORMAT),
            'analysis_end_date': analysis_end_date.strftime(DATE_FORMAT),
            'generation_date': datetime.now().strftime(f"{DATE_FORMAT} %H:%M:%S"),
            'summary': exception_summary,
            'kpis': kpis,
            'exceptions_list': exceptions_list,
            'exceptions_pagination': exceptions_pagination,
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
            'total_data_points': len(facility_data[facility_data[FileColumns.FACILITY_LOCATION_NAME] == facility]) if not facility_data.empty else 0
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