"""
Overtime hours analysis module for workforce analytics system.
Calculates overtime based on total hours worked per employee across all roles.
"""

import pandas as pd
from typing import Dict, Any, Optional
import logging
from config.constants import OVERTIME_THRESHOLD, REPORT_TOP_OVERTIME_COUNT
from src.models.data_models import OvertimeResult, EmployeeOvertimeSummary
from src.utils.role_display_mapper import get_short_display_name

logger = logging.getLogger(__name__)


def analyze_overtime(
    facility_df: pd.DataFrame,
    facility: str,
    week_start_date: Optional[pd.Timestamp] = None,
    week_end_date: Optional[pd.Timestamp] = None
) -> OvertimeResult:
    """
    Analyze overtime hours for employees in a facility.
    
    Overtime is calculated based on total hours worked by each employee
    across all roles, compared to the standard work week threshold.
    
    Args:
        facility_df: Facility hours DataFrame filtered for the specific facility
        facility: Facility name for logging and reporting
        week_start_date: Optional start date for analysis period
        week_end_date: Optional end date for analysis period
        
    Returns:
        OvertimeResult: Analysis results including top overtime employees
    """
    logger.info(f"Analyzing overtime hours for facility: {facility}")
    
    # Filter by date range if provided
    if week_start_date and week_end_date:
        facility_df = facility_df[
            (facility_df['date'] >= week_start_date) & 
            (facility_df['date'] <= week_end_date)
        ]
    
    # Group by employee to sum total hours across all roles
    employee_hours = facility_df.groupby(['employee_id', 'employee_name']).agg({
        'actual_hours': 'sum',
        'week_start': 'first'  # Get the week for grouping
    }).reset_index()
    
    # Calculate overtime hours (hours over threshold)
    employee_hours['overtime_hours'] = (
        employee_hours['actual_hours'] - OVERTIME_THRESHOLD
    ).clip(lower=0)
    
    # Filter to only employees with overtime
    overtime_employees = employee_hours[employee_hours['overtime_hours'] > 0].copy()
    
    if overtime_employees.empty:
        logger.info(f"No overtime found for facility: {facility}")
        return OvertimeResult(
            facility=facility,
            total_overtime_hours=0.0,
            employee_count=0,
            top_overtime_employees=[]
        )
    
    # For each employee with overtime, find their primary role (most hours)
    employee_summaries = []
    
    for _, emp_row in overtime_employees.iterrows():
        emp_id = emp_row['employee_id']
        emp_name = emp_row['employee_name']
        
        # Get role breakdown for this employee
        emp_roles = facility_df[facility_df['employee_id'] == emp_id].groupby('role').agg({
            'actual_hours': 'sum'
        }).reset_index()
        
        # Find the role with most hours
        primary_role = emp_roles.loc[emp_roles['actual_hours'].idxmax(), 'role']
        
        employee_summaries.append(
            EmployeeOvertimeSummary(
                employee_id=emp_id,
                employee_name=emp_name,
                total_hours=float(emp_row['actual_hours']),
                overtime_hours=float(emp_row['overtime_hours']),
                primary_role=primary_role
            )
        )
    
    # Sort by overtime hours descending and take top N
    employee_summaries.sort(key=lambda x: x.overtime_hours, reverse=True)
    top_employees = employee_summaries[:REPORT_TOP_OVERTIME_COUNT]
    
    # Calculate totals
    total_overtime = sum(emp.overtime_hours for emp in employee_summaries)
    
    logger.info(
        f"Overtime analysis complete for {facility}: "
        f"{len(employee_summaries)} employees with {total_overtime:.1f} total overtime hours"
    )
    
    return OvertimeResult(
        facility=facility,
        total_overtime_hours=total_overtime,
        employee_count=len(employee_summaries),
        top_overtime_employees=top_employees
    )


def format_overtime_display(overtime_result: OvertimeResult) -> Dict[str, Any]:
    """
    Format overtime analysis results for display in reports.
    
    Args:
        overtime_result: OvertimeResult object with analysis data
        
    Returns:
        Dict containing formatted display data
    """
    return {
        'facility': overtime_result.facility,
        'total_overtime_hours': overtime_result.total_overtime_hours,
        'employee_count': overtime_result.employee_count,
        'top_employees': [
            {
                'name': emp.employee_name,
                'total_hours': emp.total_hours,
                'overtime_hours': emp.overtime_hours,
                'primary_role': get_short_display_name(emp.primary_role)
            }
            for emp in overtime_result.top_overtime_employees
        ]
    }