"""
Unmapped Hours Analysis Module - Analyze and report on unmapped hours by category and employee.
Provides detailed breakdowns of unmapped hours for reporting purposes.
"""

import logging
import pandas as pd
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from collections import defaultdict

from src.models.data_models import (
    FacilityHours,
    UnmappedHoursResult,
    UnmappedCategorySummary
)
from src.utils.role_display_mapper import get_standard_display_name
from config.constants import FileColumns

logger = logging.getLogger(__name__)


def is_unmapped_role(role) -> bool:
    """
    Check if a role is an unmapped category.
    
    Args:
        role: Role name to check (can be string or NaN)
        
    Returns:
        bool: True if role is unmapped category, False otherwise
    """
    # Handle NaN or non-string values
    if not isinstance(role, str) or pd.isna(role):
        return False
    
    unmapped_keywords = ['unmapped', 'other unmapped']
    role_lower = role.lower()
    return any(keyword in role_lower for keyword in unmapped_keywords)


def extract_unmapped_hours_data(
    facility_data: pd.DataFrame, 
    facility: str,
    analysis_start_date: datetime,
    analysis_end_date: datetime
) -> pd.DataFrame:
    """
    Extract unmapped hours data for a specific facility within the analysis period.
    
    Args:
        facility_data: DataFrame containing facility hours data
        facility: Name of facility to analyze
        analysis_start_date: Start of analysis period
        analysis_end_date: End of analysis period
        
    Returns:
        pd.DataFrame: Filtered data containing only unmapped roles for the facility and period
    """
    logger.debug(f"Extracting unmapped hours for facility '{facility}' from {analysis_start_date} to {analysis_end_date}")
    
    # Filter for facility and date range
    facility_filtered = facility_data[
        (facility_data[FileColumns.FACILITY_LOCATION_NAME] == facility) &
        (facility_data[FileColumns.FACILITY_HOURS_DATE] >= analysis_start_date) &
        (facility_data[FileColumns.FACILITY_HOURS_DATE] <= analysis_end_date)
    ].copy()
    
    if facility_filtered.empty:
        logger.warning(f"No data found for facility '{facility}' in specified date range")
        return pd.DataFrame()
    
    # Filter for unmapped roles
    unmapped_mask = facility_filtered[FileColumns.FACILITY_STAFF_ROLE_NAME].apply(is_unmapped_role)
    unmapped_data = facility_filtered[unmapped_mask].copy()
    
    logger.info(f"Found {len(unmapped_data)} unmapped hours records for facility '{facility}'")
    
    return unmapped_data


def aggregate_unmapped_by_category_and_employee(
    unmapped_data: pd.DataFrame,
    facility: str,
    analysis_start_date: datetime,
    analysis_end_date: datetime
) -> List[UnmappedHoursResult]:
    """
    Aggregate unmapped hours by category and employee.
    
    Args:
        unmapped_data: DataFrame containing unmapped hours data
        facility: Name of facility
        analysis_start_date: Start of analysis period
        analysis_end_date: End of analysis period
        
    Returns:
        List[UnmappedHoursResult]: Aggregated results by category and employee
    """
    if unmapped_data.empty:
        logger.info(f"No unmapped hours data to aggregate for facility '{facility}'")
        return []
    
    logger.debug(f"Aggregating unmapped hours by category and employee for facility '{facility}'")
    
    # Group by role (category), employee ID, and employee name
    grouped = unmapped_data.groupby([
        FileColumns.FACILITY_STAFF_ROLE_NAME, 
        FileColumns.FACILITY_EMPLOYEE_ID, 
        FileColumns.FACILITY_EMPLOYEE_NAME
    ])[FileColumns.FACILITY_TOTAL_HOURS].sum().reset_index()
    
    # Calculate category totals for percentage calculations
    category_totals = unmapped_data.groupby(FileColumns.FACILITY_STAFF_ROLE_NAME)[FileColumns.FACILITY_TOTAL_HOURS].sum().to_dict()
    
    results = []
    
    for _, row in grouped.iterrows():
        category = row[FileColumns.FACILITY_STAFF_ROLE_NAME]
        employee_id = str(row[FileColumns.FACILITY_EMPLOYEE_ID])
        employee_name = row[FileColumns.FACILITY_EMPLOYEE_NAME]
        total_hours = float(row[FileColumns.FACILITY_TOTAL_HOURS])
        
        # Calculate percentage of this category's total
        category_total = category_totals.get(category, 0)
        percentage_of_category = (total_hours / category_total * 100) if category_total > 0 else 0
        
        result = UnmappedHoursResult(
            facility=facility,
            category=category,
            employee_name=employee_name,
            employee_id=employee_id,
            total_hours=total_hours,
            percentage_of_category=percentage_of_category,
            analysis_period_start=analysis_start_date,
            analysis_period_end=analysis_end_date
        )
        
        results.append(result)
    
    # Sort by category, then by hours descending
    results.sort(key=lambda x: (x.category, -x.total_hours))
    
    logger.info(f"Aggregated {len(results)} unmapped hours entries across {len(category_totals)} categories")
    
    return results


def calculate_unmapped_summary_stats(
    unmapped_results: List[UnmappedHoursResult],
    facility: str,
    analysis_start_date: datetime,
    analysis_end_date: datetime
) -> List[UnmappedCategorySummary]:
    """
    Calculate summary statistics for unmapped categories.
    
    Args:
        unmapped_results: List of unmapped hours results
        facility: Name of facility
        analysis_start_date: Start of analysis period
        analysis_end_date: End of analysis period
        
    Returns:
        List[UnmappedCategorySummary]: Summary statistics by category
    """
    if not unmapped_results:
        logger.info(f"No unmapped results to summarize for facility '{facility}'")
        return []
    
    logger.debug(f"Calculating summary statistics for unmapped categories in facility '{facility}'")
    
    # Group results by category
    category_data = defaultdict(list)
    for result in unmapped_results:
        category_data[result.category].append(result)
    
    # Calculate total unmapped hours across all categories
    total_unmapped_hours = sum(result.total_hours for result in unmapped_results)
    
    summaries = []
    
    for category, results in category_data.items():
        category_total_hours = sum(result.total_hours for result in results)
        employee_count = len(results)
        percentage_of_total_unmapped = (category_total_hours / total_unmapped_hours * 100) if total_unmapped_hours > 0 else 0
        average_hours_per_employee = category_total_hours / employee_count if employee_count > 0 else 0
        
        summary = UnmappedCategorySummary(
            facility=facility,
            category=category,
            total_hours=category_total_hours,
            employee_count=employee_count,
            percentage_of_total_unmapped=percentage_of_total_unmapped,
            average_hours_per_employee=average_hours_per_employee,
            analysis_period_start=analysis_start_date,
            analysis_period_end=analysis_end_date
        )
        
        summaries.append(summary)
    
    # Sort by total hours descending
    summaries.sort(key=lambda x: -x.total_hours)
    
    logger.info(f"Generated summary statistics for {len(summaries)} unmapped categories")
    
    return summaries


def analyze_unmapped_hours_for_facility(
    facility_data: pd.DataFrame,
    facility: str,
    analysis_start_date: datetime,
    analysis_end_date: datetime
) -> Tuple[List[UnmappedHoursResult], List[UnmappedCategorySummary]]:
    """
    Complete unmapped hours analysis for a facility.
    
    Args:
        facility_data: DataFrame containing facility hours data
        facility: Name of facility to analyze
        analysis_start_date: Start of analysis period
        analysis_end_date: End of analysis period
        
    Returns:
        Tuple containing:
        - List[UnmappedHoursResult]: Detailed results by employee and category
        - List[UnmappedCategorySummary]: Summary statistics by category
    """
    logger.info(f"Starting unmapped hours analysis for facility '{facility}'")
    
    try:
        # Extract unmapped hours data
        unmapped_data = extract_unmapped_hours_data(
            facility_data, facility, analysis_start_date, analysis_end_date
        )
        
        # Aggregate by category and employee
        unmapped_results = aggregate_unmapped_by_category_and_employee(
            unmapped_data, facility, analysis_start_date, analysis_end_date
        )
        
        # Calculate summary statistics
        category_summaries = calculate_unmapped_summary_stats(
            unmapped_results, facility, analysis_start_date, analysis_end_date
        )
        
        logger.info(f"Completed unmapped hours analysis for facility '{facility}': "
                   f"{len(unmapped_results)} detailed entries, {len(category_summaries)} categories")
        
        return unmapped_results, category_summaries
        
    except Exception as e:
        logger.error(f"Error analyzing unmapped hours for facility '{facility}': {str(e)}")
        raise


def format_unmapped_hours_for_display(
    unmapped_results: List[UnmappedHoursResult],
    category_summaries: List[UnmappedCategorySummary]
) -> Dict[str, any]:
    """
    Format unmapped hours data for display in reports.
    
    Args:
        unmapped_results: Detailed unmapped hours results
        category_summaries: Category summary statistics
        
    Returns:
        Dict containing formatted data for report templates
    """
    if not unmapped_results and not category_summaries:
        return {
            'has_unmapped_hours': False,
            'total_unmapped_hours': 0,
            'total_categories': 0,
            'total_employees': 0,
            'categories': [],
            'detailed_results': []
        }
    
    # Calculate overall totals
    total_unmapped_hours = sum(summary.total_hours for summary in category_summaries)
    total_categories = len(category_summaries)
    total_employees = len(set(result.employee_id for result in unmapped_results))
    
    # Group detailed results by category for display
    category_details = defaultdict(list)
    for result in unmapped_results:
        category_details[result.category].append({
            'employee_name': result.employee_name,
            'employee_id': result.employee_id,
            'total_hours': result.total_hours,
            'percentage_of_category': result.percentage_of_category
        })
    
    # Combine with summaries for complete category information
    categories_for_display = []
    for summary in category_summaries:
        # Get display name for category
        display_name = get_standard_display_name(summary.category)
        
        category_info = {
            'category': summary.category,
            'display_name': display_name,
            'total_hours': summary.total_hours,
            'employee_count': summary.employee_count,
            'percentage_of_total_unmapped': summary.percentage_of_total_unmapped,
            'average_hours_per_employee': summary.average_hours_per_employee,
            'employees': category_details.get(summary.category, [])
        }
        categories_for_display.append(category_info)
    
    return {
        'has_unmapped_hours': True,
        'total_unmapped_hours': total_unmapped_hours,
        'total_categories': total_categories,
        'total_employees': total_employees,
        'categories': categories_for_display,
        'detailed_results': unmapped_results
    }