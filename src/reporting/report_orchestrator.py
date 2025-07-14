"""
Report orchestrator - Coordinates the complete PDF report generation process.
Integrates all F-6 components: charts, templates, PDF generation, and facility iteration.
"""

import asyncio
import pandas as pd
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from config.settings import AppSettings
from config.constants import FileColumns
from src.models.data_models import (
    StatisticalSummary,
    TrendAnalysisResult, 
    ReportMetadata,
    DataQualityException
)
from src.reporting.pdf_generator import PDFReportGenerator, check_pdf_generation_availability
from src.reporting.exceptions import (
    filter_exceptions_by_facility,
    generate_facility_exception_summary,
    generate_exceptions_summary_table
)
from src.utils.error_handlers import ReportGenerationError, ErrorCollector, handle_exceptions
from src.utils.logging_config import TimedOperation


logger = logging.getLogger(__name__)


class ReportOrchestrator:
    """
    Orchestrates the complete report generation process for all facilities.
    """
    
    def __init__(self, settings: AppSettings):
        """
        Initialize report orchestrator.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.pdf_generator = PDFReportGenerator(
            output_dir=settings.directories.reports_dir,
            timeout_seconds=settings.pdf_timeout_seconds
        )
        self.error_collector = ErrorCollector(max_errors=50)
        
        logger.info("Report orchestrator initialized")
    
    async def generate_all_facility_reports(self,
                                          exceptions_df: pd.DataFrame,
                                          facility_data: pd.DataFrame,
                                          model_data: pd.DataFrame,
                                          statistics: List[StatisticalSummary],
                                          trend_results: List[TrendAnalysisResult],
                                          analysis_start_date: datetime,
                                          analysis_end_date: datetime,
                                          daily_facility_data: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """
        Generate PDF reports for all facilities with exceptions.
        
        Args:
            exceptions_df: DataFrame with compiled exceptions
            facility_data: DataFrame with facility hours data
            model_data: DataFrame with model hours data
            statistics: List of statistical summaries
            trend_results: List of trend analysis results
            analysis_start_date: Start date of analysis period
            analysis_end_date: End date of analysis period
            daily_facility_data: Optional daily facility data for trend charts
            
        Returns:
            Dictionary with generation results and summary
        """
        if not check_pdf_generation_availability():
            logger.warning("PDF generation not available - skipping report generation")
            return {
                'success': False,
                'error': 'PDF generation not available (Playwright not installed)',
                'generated_reports': [],
                'summary': {}
            }
        
        logger.info("Starting comprehensive facility report generation")
        
        with TimedOperation(logger, "Complete Report Generation"):
            
            # Determine which facilities to process
            facilities_to_process = self._get_facilities_to_process(
                exceptions_df, facility_data
            )
            
            if not facilities_to_process:
                logger.warning("No facilities to process for report generation")
                return {
                    'success': True,
                    'generated_reports': [],
                    'summary': {'message': 'No facilities require reports'},
                    'facilities_processed': 0
                }
            
            logger.info(f"Processing {len(facilities_to_process)} facilities for report generation")
            
            # Generate reports
            generated_reports = await self._generate_reports_for_facilities(
                facilities_to_process,
                exceptions_df,
                facility_data, 
                model_data,
                statistics,
                trend_results,
                analysis_start_date,
                analysis_end_date,
                daily_facility_data
            )
            
            # Create summary
            summary = self._create_generation_summary(
                generated_reports, facilities_to_process, exceptions_df
            )
            
            # Log results
            self._log_generation_results(generated_reports, summary)
            
            return {
                'success': len(generated_reports) > 0 or len(facilities_to_process) == 0,
                'generated_reports': generated_reports,
                'summary': summary,
                'facilities_processed': len(facilities_to_process),
                'errors': self.error_collector.get_error_summary() if self.error_collector.has_errors() else None
            }
    
    def _get_facilities_to_process(self, 
                                  exceptions_df: pd.DataFrame,
                                  facility_data: pd.DataFrame) -> List[str]:
        """
        Determine which facilities need report generation.
        
        Args:
            exceptions_df: DataFrame with exceptions
            facility_data: DataFrame with facility data
            
        Returns:
            List of facility names to process
        """
        if self.settings.generate_only_exceptions:
            # Only facilities with exceptions
            if exceptions_df.empty:
                logger.info("No exceptions found - no reports to generate in exceptions-only mode")
                return []
            
            facilities_with_exceptions = exceptions_df['facility'].unique().tolist()
            logger.info(f"Exceptions-only mode: {len(facilities_with_exceptions)} facilities with exceptions")
            return facilities_with_exceptions
        else:
            # All facilities in the data
            all_facilities = facility_data[FileColumns.FACILITY_LOCATION_NAME].unique().tolist()
            logger.info(f"Generating reports for all {len(all_facilities)} facilities")
            return all_facilities
    
    async def _generate_reports_for_facilities(self,
                                             facilities: List[str],
                                             exceptions_df: pd.DataFrame,
                                             facility_data: pd.DataFrame,
                                             model_data: pd.DataFrame,
                                             statistics: List[StatisticalSummary],
                                             trend_results: List[TrendAnalysisResult],
                                             analysis_start_date: datetime,
                                             analysis_end_date: datetime,
                                             daily_facility_data: Optional[pd.DataFrame] = None) -> List[str]:
        """
        Generate PDF reports for the specified facilities.
        
        Args:
            facilities: List of facility names
            exceptions_df: DataFrame with exceptions
            facility_data: DataFrame with facility data
            model_data: DataFrame with model data
            statistics: Statistical summaries
            trend_results: Trend analysis results
            analysis_start_date: Analysis start date
            analysis_end_date: Analysis end date
            daily_facility_data: Optional daily facility data for trend charts
            
        Returns:
            List of paths to successfully generated PDF files
        """
        generated_reports = []
        
        for i, facility in enumerate(facilities, 1):
            try:
                logger.info(f"Generating report {i}/{len(facilities)}: {facility}")
                
                with TimedOperation(logger, f"Report generation for {facility}", log_entry=False):
                    pdf_path = await self.pdf_generator.generate_facility_report(
                        facility=facility,
                        exceptions_df=exceptions_df,
                        facility_data=facility_data,
                        model_data=model_data,
                        statistics=statistics,
                        trend_results=trend_results,
                        analysis_start_date=analysis_start_date,
                        analysis_end_date=analysis_end_date,
                        daily_facility_data=daily_facility_data
                    )
                    
                    generated_reports.append(pdf_path)
                    logger.info(f"✅ Successfully generated report for {facility}")
                
            except Exception as e:
                error_msg = f"Failed to generate report for {facility}: {str(e)}"
                logger.error(error_msg)
                self.error_collector.add_error(
                    ReportGenerationError(error_msg, facility=facility),
                    context=f"Report generation for {facility}"
                )
                continue
        
        return generated_reports
    
    def _create_generation_summary(self,
                                  generated_reports: List[str],
                                  facilities_processed: List[str],
                                  exceptions_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Create summary of report generation results.
        
        Args:
            generated_reports: List of generated report paths
            facilities_processed: List of facilities that were processed
            exceptions_df: DataFrame with exceptions
            
        Returns:
            Dictionary with summary information
        """
        # Basic statistics
        total_facilities = len(facilities_processed)
        successful_reports = len(generated_reports)
        failed_reports = total_facilities - successful_reports
        
        # Exception statistics
        total_exceptions = len(exceptions_df)
        facilities_with_exceptions = exceptions_df['facility'].nunique() if not exceptions_df.empty else 0
        
        # Report file information
        report_summary = self.pdf_generator.get_report_summary(generated_reports)
        
        summary = {
            'generation_timestamp': datetime.now(),
            'total_facilities_processed': total_facilities,
            'successful_reports': successful_reports,
            'failed_reports': failed_reports,
            'success_rate': (successful_reports / total_facilities * 100) if total_facilities > 0 else 0,
            'total_exceptions_analyzed': total_exceptions,
            'facilities_with_exceptions': facilities_with_exceptions,
            'output_directory': self.settings.directories.reports_dir,
            'exceptions_only_mode': self.settings.generate_only_exceptions,
            'report_files': report_summary,
            'processing_errors': self.error_collector.has_errors()
        }
        
        return summary
    
    def _log_generation_results(self, 
                               generated_reports: List[str],
                               summary: Dict[str, Any]) -> None:
        """
        Log comprehensive results of report generation.
        
        Args:
            generated_reports: List of generated report paths
            summary: Summary dictionary
        """
        logger.info("=" * 60)
        logger.info("REPORT GENERATION COMPLETE")
        logger.info("=" * 60)
        
        logger.info(f"Facilities Processed: {summary['total_facilities_processed']}")
        logger.info(f"Successful Reports: {summary['successful_reports']}")
        logger.info(f"Failed Reports: {summary['failed_reports']}")
        logger.info(f"Success Rate: {summary['success_rate']:.1f}%")
        
        if summary['total_exceptions_analyzed'] > 0:
            logger.info(f"Total Exceptions Analyzed: {summary['total_exceptions_analyzed']}")
            logger.info(f"Facilities with Exceptions: {summary['facilities_with_exceptions']}")
        
        logger.info(f"Output Directory: {summary['output_directory']}")
        logger.info(f"Exceptions-Only Mode: {summary['exceptions_only_mode']}")
        
        if generated_reports:
            total_size_mb = summary['report_files']['total_size_mb']
            logger.info(f"Total Report Size: {total_size_mb:.2f} MB")
            
            logger.info("Generated Reports:")
            for report_path in generated_reports:
                facility_name = report_path.split('/')[-1].split('_')[0]
                logger.info(f"  - {facility_name}: {report_path}")
        
        # Log any errors
        if self.error_collector.has_errors():
            logger.warning(f"Encountered {len(self.error_collector.errors)} errors during generation")
            self.error_collector.log_summary()
        
        logger.info("=" * 60)
    
    async def generate_single_facility_report(self,
                                            facility: str,
                                            exceptions_df: pd.DataFrame,
                                            facility_data: pd.DataFrame,
                                            model_data: pd.DataFrame,
                                            statistics: List[StatisticalSummary],
                                            trend_results: List[TrendAnalysisResult],
                                            analysis_start_date: datetime,
                                            analysis_end_date: datetime) -> Optional[str]:
        """
        Generate PDF report for a single facility.
        
        Args:
            facility: Facility name
            exceptions_df: DataFrame with exceptions
            facility_data: DataFrame with facility data
            model_data: DataFrame with model data
            statistics: Statistical summaries
            trend_results: Trend analysis results
            analysis_start_date: Analysis start date
            analysis_end_date: Analysis end date
            
        Returns:
            Path to generated PDF file or None if failed
        """
        if not check_pdf_generation_availability():
            logger.error("PDF generation not available")
            return None
        
        try:
            logger.info(f"Generating single facility report for {facility}")
            
            pdf_path = await self.pdf_generator.generate_facility_report(
                facility=facility,
                exceptions_df=exceptions_df,
                facility_data=facility_data,
                model_data=model_data,
                statistics=statistics,
                trend_results=trend_results,
                analysis_start_date=analysis_start_date,
                analysis_end_date=analysis_end_date
            )
            
            logger.info(f"Successfully generated single facility report: {pdf_path}")
            return pdf_path
            
        except Exception as e:
            logger.error(f"Failed to generate single facility report for {facility}: {str(e)}")
            return None
    
    def get_report_status(self) -> Dict[str, Any]:
        """
        Get status information about the report generation system.
        
        Returns:
            Dictionary with system status
        """
        return {
            'pdf_generation_available': check_pdf_generation_availability(),
            'output_directory': self.settings.directories.reports_dir,
            'exceptions_only_mode': self.settings.generate_only_exceptions,
            'template_directory': self.pdf_generator.template_dir,
            'error_count': len(self.error_collector.errors) if self.error_collector.has_errors() else 0
        }


@handle_exceptions(exit_on_error=False)
async def generate_comprehensive_reports(settings: AppSettings,
                                       exceptions_df: pd.DataFrame,
                                       facility_data: pd.DataFrame,
                                       model_data: pd.DataFrame,
                                       statistics: List[StatisticalSummary],
                                       trend_results: List[TrendAnalysisResult],
                                       analysis_start_date: datetime,
                                       analysis_end_date: datetime,
                                       data_quality_exceptions: Optional[List[DataQualityException]] = None,
                                       daily_facility_data: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
    """
    Convenience function to generate comprehensive reports for all facilities.
    
    Args:
        settings: Application settings
        exceptions_df: DataFrame with exceptions
        facility_data: DataFrame with facility data
        model_data: DataFrame with model data
        statistics: Statistical summaries
        trend_results: Trend analysis results
        analysis_start_date: Analysis start date
        analysis_end_date: Analysis end date
        data_quality_exceptions: Optional list of data quality issues found during normalization
        daily_facility_data: Optional daily facility data for trend charts
        
    Returns:
        Dictionary with generation results
    """
    orchestrator = ReportOrchestrator(settings)
    
    return await orchestrator.generate_all_facility_reports(
        exceptions_df=exceptions_df,
        facility_data=facility_data,
        model_data=model_data,
        statistics=statistics,
        trend_results=trend_results,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        daily_facility_data=daily_facility_data
    )