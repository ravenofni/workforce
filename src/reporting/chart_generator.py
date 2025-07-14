"""
Chart generation module for workforce analytics reports.
Creates statistical visualizations using matplotlib and seaborn for PDF reports.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64
from typing import List, Dict, Any, Optional, Tuple
import logging
from datetime import datetime, timedelta

from config.constants import DATE_FORMAT, FileColumns
from src.models.data_models import (
    StatisticalSummary, 
    VarianceResult, 
    TrendAnalysisResult,
    FacilityKPI
)


logger = logging.getLogger(__name__)

# Set consistent styling for all charts
plt.style.use('default')
sns.set_palette("husl")


def setup_chart_style() -> None:
    """Configure global chart styling for professional reports."""
    plt.rcParams.update({
        'figure.figsize': (12, 8),
        'figure.dpi': 100,
        'figure.facecolor': 'white',
        'axes.facecolor': 'white',
        'axes.grid': True,
        'axes.grid.alpha': 0.3,
        'axes.spines.top': False,
        'axes.spines.right': False,
        'font.size': 10,
        'font.family': ['Arial', 'DejaVu Sans', 'Liberation Sans'],
        'axes.titlesize': 14,
        'axes.labelsize': 12,
        'xtick.labelsize': 10,
        'ytick.labelsize': 10,
        'legend.fontsize': 10,
        'figure.titlesize': 16
    })


def create_variance_heatmap(exceptions_df: pd.DataFrame, facility: str) -> str:
    """
    Create variance heat-map for a facility (F-6c requirement).
    
    Args:
        exceptions_df: DataFrame with compiled exceptions
        facility: Facility name
        
    Returns:
        Base64 encoded chart image for HTML embedding
    """
    setup_chart_style()
    
    # Filter exceptions for this facility
    facility_exceptions = exceptions_df[exceptions_df['facility'] == facility].copy()
    
    if facility_exceptions.empty:
        return create_no_data_chart("No Variance Data Available", facility)
    
    try:
        # Create pivot table for heatmap
        # Use severity as the heat value
        pivot_data = facility_exceptions.pivot_table(
            index='role',
            columns='exception_type', 
            values='severity',
            aggfunc='mean',
            fill_value=0
        )
        
        if pivot_data.empty:
            return create_no_data_chart("No Variance Data for Heatmap", facility)
        
        # Create figure
        fig, ax = plt.subplots(figsize=(12, max(6, len(pivot_data.index) * 0.5)))
        
        # Create heatmap
        sns.heatmap(
            pivot_data,
            annot=True,
            fmt='.1f',
            cmap='YlOrRd',
            cbar_kws={'label': 'Severity Score'},
            ax=ax,
            linewidths=0.5
        )
        
        ax.set_title(f'Variance Severity Heat-map - {facility}', fontsize=14, fontweight='bold', pad=20)
        ax.set_xlabel('Exception Type', fontsize=12)
        ax.set_ylabel('Role', fontsize=12)
        
        # Rotate labels for better readability
        plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
        plt.setp(ax.get_yticklabels(), rotation=0)
        
        plt.tight_layout()
        
        # Convert to base64
        chart_b64 = fig_to_base64(fig)
        plt.close(fig)
        
        logger.info(f"Generated variance heatmap for {facility}")
        return chart_b64
        
    except Exception as e:
        logger.error(f"Error creating variance heatmap for {facility}: {str(e)}")
        plt.close('all')
        return create_error_chart(f"Error creating heatmap: {str(e)}")


def create_trend_charts(facility_data: pd.DataFrame, trend_results: List[TrendAnalysisResult], 
                       facility: str) -> str:
    """
    Create trend analysis charts for a facility (F-6c requirement).
    
    Args:
        facility_data: DataFrame with facility hours data
        trend_results: List of trend analysis results for the facility
        facility: Facility name
        
    Returns:
        Base64 encoded chart image for HTML embedding
    """
    setup_chart_style()
    
    # Filter data and trends for this facility
    facility_trends = [t for t in trend_results if t.facility == facility]
    facility_hours = facility_data[facility_data[FileColumns.FACILITY_LOCATION_NAME] == facility].copy()
    
    if not facility_trends or facility_hours.empty:
        return create_no_data_chart("No Trend Data Available", facility)
    
    try:
        # Create subplots for multiple roles
        n_roles = min(len(facility_trends), 6)  # Limit to 6 roles for readability
        cols = 2
        rows = (n_roles + 1) // 2
        
        fig, axes = plt.subplots(rows, cols, figsize=(15, 4 * rows))
        if rows == 1:
            axes = [axes] if cols == 1 else axes
        else:
            axes = axes.flatten()
        
        for i, trend in enumerate(facility_trends[:n_roles]):
            ax = axes[i] if n_roles > 1 else axes
            
            # Get data for this role
            role_data = facility_hours[facility_hours[FileColumns.FACILITY_STAFF_ROLE_NAME] == trend.role].copy()
            
            if not role_data.empty:
                # Sort by date and prepare for plotting
                role_data = role_data.sort_values(FileColumns.FACILITY_HOURS_DATE)
                
                # Use weekly data if available
                if 'WeekStart' in role_data.columns:
                    plot_data = role_data.groupby('WeekStart')[FileColumns.FACILITY_TOTAL_HOURS].mean().reset_index()
                    plot_data.columns = ['Date', 'Hours']
                else:
                    plot_data = role_data[[FileColumns.FACILITY_HOURS_DATE, FileColumns.FACILITY_TOTAL_HOURS]].copy()
                    plot_data.columns = ['Date', 'Hours']
                
                # Filter to trend analysis period
                plot_data = plot_data[
                    (plot_data['Date'] >= trend.analysis_start_date) & 
                    (plot_data['Date'] <= trend.analysis_end_date)
                ]
                
                if len(plot_data) >= 2:
                    # Plot actual data
                    ax.scatter(plot_data['Date'], plot_data['Hours'], alpha=0.6, s=30)
                    
                    # Add trend line
                    x_numeric = np.arange(len(plot_data))
                    trend_line = trend.slope * x_numeric + plot_data['Hours'].iloc[0]
                    ax.plot(plot_data['Date'], trend_line, 'r-', linewidth=2, alpha=0.8)
                    
                    # Formatting
                    ax.set_title(f'{trend.role}\n{trend.trend_direction.title()} trend (p={trend.p_value:.3f})', 
                               fontsize=11, fontweight='bold')
                    ax.set_xlabel('Date', fontsize=10)
                    ax.set_ylabel('Hours', fontsize=10)
                    
                    # Rotate x-axis labels
                    plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
                    
                    # Add grid
                    ax.grid(True, alpha=0.3)
                else:
                    ax.text(0.5, 0.5, 'Insufficient data', ha='center', va='center', transform=ax.transAxes)
                    ax.set_title(f'{trend.role}\nInsufficient data', fontsize=11)
            else:
                ax.text(0.5, 0.5, 'No data available', ha='center', va='center', transform=ax.transAxes)
                ax.set_title(f'{trend.role}\nNo data', fontsize=11)
        
        # Hide unused subplots
        for i in range(n_roles, len(axes)):
            axes[i].set_visible(False)
        
        plt.suptitle(f'Trend Analysis - {facility}', fontsize=16, fontweight='bold', y=0.98)
        plt.tight_layout()
        plt.subplots_adjust(top=0.93)
        
        # Convert to base64
        chart_b64 = fig_to_base64(fig)
        plt.close(fig)
        
        logger.info(f"Generated trend charts for {facility}")
        return chart_b64
        
    except Exception as e:
        logger.error(f"Error creating trend charts for {facility}: {str(e)}")
        plt.close('all')
        return create_error_chart(f"Error creating trend charts: {str(e)}")


def create_kpi_summary_chart(kpis: FacilityKPI) -> str:
    """
    Create KPI summary visualization for a facility (F-6b requirement).
    
    Args:
        kpis: FacilityKPI object with metrics
        
    Returns:
        Base64 encoded chart image for HTML embedding
    """
    setup_chart_style()
    
    try:
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        
        # 1. Model vs Actual Hours (Bar Chart)
        categories = ['Model Hours', 'Actual Hours']
        values = [kpis.total_model_hours, kpis.total_actual_hours]
        colors = ['skyblue', 'lightcoral']
        
        bars = ax1.bar(categories, values, color=colors, alpha=0.8)
        ax1.set_title('Model vs Actual Hours', fontsize=12, fontweight='bold')
        ax1.set_ylabel('Total Hours')
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + max(values)*0.01,
                    f'{height:,.0f}', ha='center', va='bottom')
        
        # 2. Exception Rate (Gauge-style)
        ax2.pie([kpis.exception_rate, 100 - kpis.exception_rate], 
               labels=['With Exceptions', 'No Exceptions'],
               colors=['red', 'lightgreen'],
               autopct='%1.1f%%',
               startangle=90)
        ax2.set_title('Roles Exception Rate', fontsize=12, fontweight='bold')
        
        # 3. Variance Distribution (if we have variance data)
        if kpis.average_variance != 0 or kpis.largest_variance != 0:
            variance_data = ['Average Variance', 'Largest Variance']
            variance_values = [abs(kpis.average_variance), abs(kpis.largest_variance)]
            
            bars = ax3.bar(variance_data, variance_values, color=['orange', 'red'], alpha=0.8)
            ax3.set_title('Variance Magnitude', fontsize=12, fontweight='bold')
            ax3.set_ylabel('Variance (%)')
            
            # Add value labels
            for bar in bars:
                height = bar.get_height()
                ax3.text(bar.get_x() + bar.get_width()/2., height + max(variance_values)*0.01,
                        f'{height:.1f}%', ha='center', va='bottom')
        else:
            ax3.text(0.5, 0.5, 'No Variance Data', ha='center', va='center', transform=ax3.transAxes)
            ax3.set_title('Variance Magnitude', fontsize=12, fontweight='bold')
        
        # 4. Role Analysis Summary
        roles_data = ['Total Roles', 'Roles with Exceptions']
        roles_values = [kpis.roles_analyzed, kpis.roles_with_exceptions]
        
        bars = ax4.bar(roles_data, roles_values, color=['lightblue', 'coral'], alpha=0.8)
        ax4.set_title('Role Analysis Summary', fontsize=12, fontweight='bold')
        ax4.set_ylabel('Number of Roles')
        
        # Add value labels
        for bar in bars:
            height = bar.get_height()
            ax4.text(bar.get_x() + bar.get_width()/2., height + max(roles_values)*0.01,
                    f'{int(height)}', ha='center', va='bottom')
        
        plt.suptitle(f'KPI Summary - {kpis.facility}', fontsize=16, fontweight='bold')
        plt.tight_layout()
        plt.subplots_adjust(top=0.93)
        
        # Convert to base64
        chart_b64 = fig_to_base64(fig)
        plt.close(fig)
        
        logger.info(f"Generated KPI summary chart for {kpis.facility}")
        return chart_b64
        
    except Exception as e:
        logger.error(f"Error creating KPI summary chart for {kpis.facility}: {str(e)}")
        plt.close('all')
        return create_error_chart(f"Error creating KPI summary: {str(e)}")


def create_control_limits_chart(statistics: List[StatisticalSummary], facility: str) -> str:
    """
    Create control limits visualization for a facility.
    
    Args:
        statistics: List of statistical summaries for the facility
        facility: Facility name
        
    Returns:
        Base64 encoded chart image for HTML embedding
    """
    setup_chart_style()
    
    facility_stats = [s for s in statistics if s.facility == facility]
    
    if not facility_stats:
        return create_no_data_chart("No Statistical Data Available", facility)
    
    try:
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # Prepare data for plotting
        roles = [s.role for s in facility_stats]
        means = [s.mean for s in facility_stats]
        ucls = [s.upper_control_limit for s in facility_stats]
        lcls = [s.lower_control_limit for s in facility_stats]
        
        x_pos = np.arange(len(roles))
        
        # Plot control limits as error bars
        ax.errorbar(x_pos, means, 
                   yerr=[np.array(means) - np.array(lcls), np.array(ucls) - np.array(means)],
                   fmt='o', capsize=5, capthick=2, markersize=8, alpha=0.8)
        
        # Add mean points
        ax.scatter(x_pos, means, color='red', s=100, zorder=5, label='Mean/Median')
        
        # Customize chart
        ax.set_xlabel('Role', fontsize=12)
        ax.set_ylabel('Hours', fontsize=12)
        ax.set_title(f'Statistical Control Limits - {facility}', fontsize=14, fontweight='bold')
        ax.set_xticks(x_pos)
        ax.set_xticklabels(roles, rotation=45, ha='right')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Convert to base64
        chart_b64 = fig_to_base64(fig)
        plt.close(fig)
        
        logger.info(f"Generated control limits chart for {facility}")
        return chart_b64
        
    except Exception as e:
        logger.error(f"Error creating control limits chart for {facility}: {str(e)}")
        plt.close('all')
        return create_error_chart(f"Error creating control limits chart: {str(e)}")


def fig_to_base64(fig) -> str:
    """
    Convert matplotlib figure to base64 string for HTML embedding.
    
    Args:
        fig: Matplotlib figure object
        
    Returns:
        Base64 encoded image string
    """
    img_buffer = io.BytesIO()
    fig.savefig(img_buffer, format='png', bbox_inches='tight', dpi=150, facecolor='white')
    img_buffer.seek(0)
    img_b64 = base64.b64encode(img_buffer.read()).decode('utf-8')
    img_buffer.close()
    return img_b64


def create_no_data_chart(message: str, facility: str = "") -> str:
    """
    Create a placeholder chart when no data is available.
    
    Args:
        message: Message to display
        facility: Facility name (optional)
        
    Returns:
        Base64 encoded placeholder image
    """
    setup_chart_style()
    
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.text(0.5, 0.5, message, ha='center', va='center', 
           transform=ax.transAxes, fontsize=16, color='gray')
    
    if facility:
        ax.set_title(f'{facility} - {message}', fontsize=14, fontweight='bold')
    
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xticks([])
    ax.set_yticks([])
    
    for spine in ax.spines.values():
        spine.set_visible(False)
    
    plt.tight_layout()
    
    chart_b64 = fig_to_base64(fig)
    plt.close(fig)
    
    return chart_b64


def create_error_chart(error_message: str) -> str:
    """
    Create an error chart when chart generation fails.
    
    Args:
        error_message: Error message to display
        
    Returns:
        Base64 encoded error image
    """
    setup_chart_style()
    
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.text(0.5, 0.5, f'Chart Generation Error:\n{error_message}', 
           ha='center', va='center', transform=ax.transAxes, 
           fontsize=12, color='red', bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow"))
    
    ax.set_title('Chart Generation Failed', fontsize=14, fontweight='bold', color='red')
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xticks([])
    ax.set_yticks([])
    
    for spine in ax.spines.values():
        spine.set_visible(False)
    
    plt.tight_layout()
    
    chart_b64 = fig_to_base64(fig)
    plt.close(fig)
    
    return chart_b64


def cleanup_matplotlib() -> None:
    """Clean up matplotlib resources to prevent memory leaks."""
    plt.close('all')
    plt.cla()
    plt.clf()