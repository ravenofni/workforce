"""
Statistical analysis engine (F-3a, F-3b) - Descriptive statistics and control limits.
Migrates and enhances patterns from examples/data_processing.py.
"""

import pandas as pd
import numpy as np
from scipy.stats import shapiro
from typing import Dict, List, Tuple, Optional
import logging

from config.constants import (
    NORMALITY_P_VALUE_THRESHOLD,
    CONTROL_LIMIT_MULTIPLIER,
    MIN_SAMPLE_SIZE_NORMALITY,
    MAX_SAMPLE_SIZE_NORMALITY,
    ControlMethod,
    FileColumns
)
from src.models.data_models import StatisticalSummary


logger = logging.getLogger(__name__)


def calculate_descriptive_statistics(data: pd.Series) -> Dict[str, float]:
    """
    Calculate comprehensive descriptive statistics for a data series.
    
    Args:
        data: Pandas Series containing numerical data
        
    Returns:
        Dictionary with descriptive statistics
    """
    if data.empty:
        return {
            'n': 0,
            'mean': 0.0,
            'median': 0.0,
            'std': 0.0,
            'mad': 0.0,
            'min': 0.0,
            'max': 0.0,
            'range': 0.0,
            'q25': 0.0,
            'q75': 0.0,
            'iqr': 0.0,
            'skewness': 0.0,
            'kurtosis': 0.0
        }
    
    # Remove null values
    clean_data = data.dropna()
    n = len(clean_data)
    
    if n == 0:
        return calculate_descriptive_statistics(pd.Series())
    
    # Basic statistics
    mean = float(clean_data.mean())
    median = float(clean_data.median())
    std = float(clean_data.std()) if n > 1 else 0.0
    
    # Median Absolute Deviation
    mad = float(np.median(np.abs(clean_data - median))) if n > 0 else 0.0
    
    # Range statistics
    min_val = float(clean_data.min())
    max_val = float(clean_data.max())
    data_range = max_val - min_val
    
    # Quartiles and IQR
    if n >= 4:
        q25, q75 = np.percentile(clean_data, [25, 75])
        iqr = q75 - q25
    else:
        q25 = q75 = iqr = 0.0
    
    # Shape statistics
    skewness = float(clean_data.skew()) if n > 2 else 0.0
    kurtosis = float(clean_data.kurtosis()) if n > 3 else 0.0
    
    return {
        'n': n,
        'mean': round(mean, 2),
        'median': round(median, 2),
        'std': round(std, 2),
        'mad': round(mad, 2),
        'min': round(min_val, 2),
        'max': round(max_val, 2),
        'range': round(data_range, 2),
        'q25': round(q25, 2),
        'q75': round(q75, 2),
        'iqr': round(iqr, 2),
        'skewness': round(skewness, 2),
        'kurtosis': round(kurtosis, 2)
    }


def test_normality(data: pd.Series) -> Tuple[bool, float, str]:
    """
    Test data for normality using Shapiro-Wilk test.
    Mirrors examples/data_processing.py normality_test function.
    
    Args:
        data: Pandas Series containing numerical data
        
    Returns:
        Tuple of (is_normal, p_value, status_message)
    """
    clean_data = data.dropna()
    n = len(clean_data)
    
    if n < MIN_SAMPLE_SIZE_NORMALITY:
        return False, 0.0, 'Lacks Data'
    
    # Check for zero range (all values identical)
    data_range = clean_data.max() - clean_data.min() if n > 0 else 0
    if data_range == 0:
        return False, 0.0, 'Zero Range'
    
    # CRITICAL: Handle scipy.stats.shapiro sample size limitations (3 <= n <= 5000)
    if n > MAX_SAMPLE_SIZE_NORMALITY:
        logger.warning(f"Sample size {n} exceeds maximum for Shapiro-Wilk test, using last {MAX_SAMPLE_SIZE_NORMALITY} values")
        clean_data = clean_data.iloc[-MAX_SAMPLE_SIZE_NORMALITY:]
        n = len(clean_data)
    
    try:
        stat, p_value = shapiro(clean_data)
        is_normal = p_value > NORMALITY_P_VALUE_THRESHOLD
        
        status = 'Normal' if is_normal else 'Not Normal'
        
        logger.debug(f"Normality test: n={n}, p-value={p_value:.4f}, result={status}")
        
        return is_normal, float(p_value), status
        
    except Exception as e:
        logger.error(f"Error in normality test: {str(e)}")
        return False, 0.0, 'Test Failed'


def calculate_control_limits(data: pd.Series) -> Dict[str, any]:
    """
    Calculate control limits using appropriate method based on normality.
    Mirrors examples/data_processing.py calculate_control_limits function.
    
    Args:
        data: Pandas Series containing numerical data
        
    Returns:
        Dictionary with control limits and method used
    """
    if data.empty:
        return {
            'mean': 0.0,
            'ucl': 0.0,
            'lcl': 0.0,
            'std': 0.0,
            'method': ControlMethod.NORMAL.value,
            'is_normal': False,
            'p_value': 0.0
        }
    
    clean_data = data.dropna()
    
    # Test for normality
    is_normal, p_value, status = test_normality(clean_data)
    
    if is_normal:
        # Use normal distribution method (mean ± 3σ)
        mean_val = float(clean_data.mean())
        std_val = float(clean_data.std())
        
        ucl = mean_val + (CONTROL_LIMIT_MULTIPLIER * std_val)
        lcl = max(mean_val - (CONTROL_LIMIT_MULTIPLIER * std_val), 0)  # Cannot be negative
        
        method = ControlMethod.NORMAL.value
        central_line = mean_val
        variability_measure = std_val
        
        logger.debug(f"Normal distribution control limits: UCL={ucl:.2f}, LCL={lcl:.2f}")
        
    else:
        # Use robust method (median ± 3×MAD)
        median_val = float(clean_data.median())
        mad_val = float(np.median(np.abs(clean_data - median_val)))
        
        ucl = median_val + (CONTROL_LIMIT_MULTIPLIER * mad_val)
        lcl = max(median_val - (CONTROL_LIMIT_MULTIPLIER * mad_val), 0)  # Cannot be negative
        
        method = ControlMethod.MAD.value
        central_line = median_val
        variability_measure = mad_val
        
        logger.debug(f"MAD-based control limits: UCL={ucl:.2f}, LCL={lcl:.2f}")
    
    return {
        'mean': round(central_line, 2),
        'ucl': round(ucl, 2),
        'lcl': round(lcl, 2),
        'std': round(variability_measure, 2),
        'method': method,
        'is_normal': is_normal,
        'p_value': round(p_value, 4)
    }


def calculate_facility_role_statistics(df: pd.DataFrame, model_df: Optional[pd.DataFrame] = None) -> List[StatisticalSummary]:
    """
    Calculate descriptive statistics for each facility-role combination (F-3a).
    Migrates examples/data_processing.py descriptive_stats_by_role_facility function.
    
    Args:
        df: DataFrame with facility hours data
        model_df: Optional DataFrame with model hours data
        
    Returns:
        List of StatisticalSummary objects
    """
    if df.empty:
        logger.warning("Empty DataFrame provided for facility-role statistics")
        return []
    
    results = []
    
    # Group by facility and role
    grouped = df.groupby([FileColumns.FACILITY_LOCATION_NAME, FileColumns.FACILITY_STAFF_ROLE_NAME])
    
    logger.info(f"Calculating statistics for {len(grouped)} facility-role combinations")
    
    for (facility, role), group in grouped:
        try:
            actual_hours = group[FileColumns.FACILITY_TOTAL_HOURS].dropna()
            
            if actual_hours.empty:
                logger.warning(f"No valid hours data for {facility} - {role}")
                continue
            
            # Calculate descriptive statistics
            desc_stats = calculate_descriptive_statistics(actual_hours)
            
            # Calculate control limits
            control_limits = calculate_control_limits(actual_hours)
            
            # Create StatisticalSummary object
            summary = StatisticalSummary(
                facility=facility,
                role=role,
                n_samples=desc_stats['n'],
                mean=desc_stats['mean'],
                median=desc_stats['median'],
                std_dev=desc_stats['std'],
                mad=desc_stats['mad'],
                control_method=ControlMethod(control_limits['method']),
                upper_control_limit=control_limits['ucl'],
                lower_control_limit=control_limits['lcl'],
                is_normal_distribution=control_limits['is_normal'],
                normality_p_value=control_limits['p_value']
            )
            
            results.append(summary)
            
        except Exception as e:
            logger.error(f"Error calculating statistics for {facility} - {role}: {str(e)}")
            continue
    
    logger.info(f"Successfully calculated statistics for {len(results)} facility-role combinations")
    return results


def detect_control_violations(data: pd.Series, control_limits: Dict[str, any]) -> List[Dict[str, any]]:
    """
    Detect control limit violations in data series.
    
    Args:
        data: Time series data to check for violations
        control_limits: Dictionary with UCL, LCL, and other control parameters
        
    Returns:
        List of violation details
    """
    violations = []
    
    if data.empty or not control_limits:
        return violations
    
    ucl = control_limits.get('ucl', float('inf'))
    lcl = control_limits.get('lcl', 0)
    
    # Check each data point
    for idx, value in data.items():
        if pd.isna(value):
            continue
        
        violation_type = None
        if value > ucl:
            violation_type = 'upper'
        elif value < lcl:
            violation_type = 'lower'
        
        if violation_type:
            violations.append({
                'index': idx,
                'value': round(float(value), 2),
                'violation_type': violation_type,
                'limit_exceeded': ucl if violation_type == 'upper' else lcl,
                'magnitude': round(abs(value - (ucl if violation_type == 'upper' else lcl)), 2)
            })
    
    return violations


def generate_statistics_summary_table(statistics: List[StatisticalSummary]) -> pd.DataFrame:
    """
    Generate a summary table of statistics for display.
    
    Args:
        statistics: List of StatisticalSummary objects
        
    Returns:
        DataFrame formatted for display
    """
    if not statistics:
        return pd.DataFrame()
    
    # Convert to DataFrame for easy manipulation
    data = []
    for stat in statistics:
        data.append({
            'Facility': stat.facility,
            'Role': stat.role,
            'N': stat.n_samples,
            'Mean': stat.mean,
            'Median': stat.median,
            'Std/MAD': stat.std_dev,
            'UCL': stat.upper_control_limit,
            'LCL': stat.lower_control_limit,
            'Method': stat.control_method.value,
            'Normal': 'Yes' if stat.is_normal_distribution else 'No'
        })
    
    df = pd.DataFrame(data)
    
    # Sort by facility and role for consistent output
    df = df.sort_values(['Facility', 'Role']).reset_index(drop=True)
    
    return df


def display_statistics_table(statistics: List[StatisticalSummary]) -> None:
    """
    Display statistics in formatted console table.
    Mirrors examples output formatting patterns.
    
    Args:
        statistics: List of StatisticalSummary objects to display
    """
    if not statistics:
        print("No statistics available to display.")
        return
    
    print("\n" + "="*100)
    print("DESCRIPTIVE STATISTICS BY FACILITY AND ROLE")
    print("="*100)
    
    # Create display DataFrame
    df = generate_statistics_summary_table(statistics)
    
    # Define column widths for formatted output
    col_widths = {
        'Facility': 20,
        'Role': 25,
        'N': 5,
        'Mean': 8,
        'Median': 8,
        'Std/MAD': 8,
        'UCL': 8,
        'LCL': 8,
        'Method': 8,
        'Normal': 6
    }
    
    # Header
    header_cols = list(col_widths.keys())
    header_fmt = ''.join([f'{{:<{col_widths[col]}}}' for col in header_cols])
    print(header_fmt.format(*header_cols))
    print("-" * 100)
    
    # Data rows
    for _, row in df.iterrows():
        row_data = [
            str(row['Facility'])[:col_widths['Facility']-1],
            str(row['Role'])[:col_widths['Role']-1],
            str(row['N']),
            f"{row['Mean']:.2f}",
            f"{row['Median']:.2f}",
            f"{row['Std/MAD']:.2f}",
            f"{row['UCL']:.2f}",
            f"{row['LCL']:.2f}",
            str(row['Method']),
            str(row['Normal'])
        ]
        
        print(header_fmt.format(*row_data))
    
    print("="*100 + "\n")
    
    # Summary statistics
    total_combinations = len(statistics)
    normal_count = sum(1 for s in statistics if s.is_normal_distribution)
    
    print(f"Summary: {total_combinations} facility-role combinations analyzed")
    print(f"Normal distributions: {normal_count} ({normal_count/total_combinations*100:.1f}%)")
    print(f"Non-normal distributions: {total_combinations-normal_count} ({(total_combinations-normal_count)/total_combinations*100:.1f}%)")
    print("")