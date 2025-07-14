import pandas as pd
import os
from datetime import timedelta
import numpy as np
from scipy.stats import shapiro
from report_assembly import detect_control_violations

def pct_fmt(val):    
    return f"{val:05.2f}%"

def get_model_hours_df(df):
    """
    Given a DataFrame with 'Facility', 'Role', and 'ModelHours' columns,
    returns a DataFrame with unique Facility, Role, and ModelHours (rounded to 2 decimals).
    """
    df = df.copy()
    df['Facility'] = df['Facility'].astype(str).str.strip()
    df['Role'] = df['Role'].astype(str).str.strip()
    unique_model_hours = df.drop_duplicates(subset=['Facility', 'Role'], keep='first')[['Facility', 'Role', 'ModelHours']]
    unique_model_hours['ModelHours'] = unique_model_hours['ModelHours'].round(2)
    return unique_model_hours.reset_index(drop=True)


def load_and_preprocess_data(file_path):
    """
    Loads the CSV data, selects and renames relevant columns,
    strips whitespace from column names, converts 'Date' column to datetime,
    and captures MODEL_HOURS for each Facility-Role combination as a DataFrame.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Data file not found: {file_path}")

    df = pd.read_csv(file_path)

    # Define the mapping from new file columns to internal script column names
    column_mapping = {
        'LOCATION_KEY': 'LocationKey',
        'LOCATION_NAME': 'Facility',
        'CENSUS_DATE': 'Date',
        'DAY_OF_WEEK': 'DayOfWeek',
        'DAY_NUMBER': 'DayofWeekNumber',
        'MODEL_MINUTES': 'ModelMinutes',
        'MODEL_HOURS': 'ModelHours',
        'ACTUAL_MINUTES': 'ActualMinutes',
        'ACTUAL_HOURS': 'ActualHours',
        'OVER_UNDER_HOURS': 'OverUnderHours',
        'STAFF_ROLE_NAME': 'Role',
        'COST_CENTER': 'CostCenter',
        'COST_CENTER_SORT': 'CostCenterSort',
        'WORKFORCE_MODEL_ROLE_SORT': 'RoleSort'
    }

    # Select only the columns we need and rename them
    missing_cols = [col for col in column_mapping.keys() if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing expected columns in the data file: {', '.join(missing_cols)}")

    df = df[list(column_mapping.keys())].rename(columns=column_mapping)
    df.columns = df.columns.str.strip()
    df['Date'] = pd.to_datetime(df['Date'])

    # --- Aggregate to weekly ---
    weekly_df = aggregate_to_weekly(df)

    # --- Capture ModelHours for each Facility-Role combination as a DataFrame (from weekly data) ---
    model_hours_df = get_model_hours_df(weekly_df)

    print(f"Data loaded and preprocessed from: {file_path}")
    print("DataFrame columns after preprocessing:", df.columns.tolist())
    print("\nCaptured Model Hours per Facility-Role (sample):")
    print(model_hours_df.head())
    if len(model_hours_df) > 5: print("  ...")
    print("\nSample of weekly aggregated data:")
    print(weekly_df.head())
    if len(weekly_df) > 5: print("  ...")

    return weekly_df, model_hours_df # Return weekly DataFrame and model hours

def get_week_start(date):
    """
    Given a pandas Timestamp, return the date of the Sunday for that week.
    """
    return date - pd.Timedelta(days=date.weekday() + 1) if date.weekday() != 6 else date

def aggregate_to_weekly(df):
    """
    Aggregates daily data to weekly sums (Sunday-Saturday) for each Facility-Role.
    Adds a 'WeekStart' column (Sunday of each week).
    Sums ActualHours, ModelHours, and other relevant numeric columns.
    Retains CostCenter, CostCenterSort, and RoleSort for sorting/grouping.
    """
    df = df.copy()
    df['WeekStart'] = df['Date'].apply(get_week_start)
    agg_cols = ['ActualHours', 'ModelHours', 'ModelMinutes', 'ActualMinutes', 'OverUnderHours']
    group_cols = ['Facility', 'Role', 'WeekStart']
    # Only sum columns that exist in the DataFrame
    sum_cols = [col for col in agg_cols if col in df.columns]
    weekly_df = df.groupby(group_cols)[sum_cols].sum().reset_index()
    # Merge in CostCenter, CostCenterSort, and RoleSort for sorting/grouping
    merge_cols = ['Facility', 'Role', 'CostCenter', 'CostCenterSort', 'RoleSort']
    available_merge_cols = [col for col in merge_cols if col in df.columns]
    if available_merge_cols:
        weekly_df = weekly_df.merge(
            df[available_merge_cols].drop_duplicates(),
            on=['Facility', 'Role'],
            how='left'
        )
    return weekly_df

def calculate_control_limits(df_for_limits): 
    """
    Calculates Mean (or Median), Upper Control Limit (UCL), and Lower Control Limit (LCL)
    for weekly 'ActualHours' for each unique (Facility, Role) combination.
    Tests normality for each group. If normal, uses mean/std; if not, uses median/MAD.    
    """
    control_limits = {}
    for facility in df_for_limits['Facility'].unique():
        for role in df_for_limits['Role'].unique():
            subset_for_limits = df_for_limits[(df_for_limits['Facility'] == facility) & (df_for_limits['Role'] == role)]
            if not subset_for_limits.empty:
                actual_hours = subset_for_limits['ActualHours'].dropna()
                if len(actual_hours) > 4500:
                    actual_hours = actual_hours.iloc[-4500:]
                norm_result = normality_test(actual_hours)
                if norm_result == 'True':
                    mean_val = actual_hours.mean()
                    std_val = actual_hours.std()
                    ucl = mean_val + (3 * std_val)
                    lcl = max(mean_val - (3 * std_val), 0)
                    method = 'Normal'
                else:
                    median_val = actual_hours.median()                    
                    madm = np.median(np.abs(actual_hours - median_val))
                    mean_val = median_val   # Use median as mean for non-normal data
                    std_val = madm          # Use MAD as std for non-normal data
                    ucl = median_val + (3 * madm)
                    lcl = max(median_val - (3 * madm), 0)
                    method = 'Modified'
                control_limits[f"{facility}_{role}"] = {
                    'mean': mean_val,
                    'ucl': ucl,
                    'lcl': lcl,
                    'std': std_val,
                    'method': method
                }
    return control_limits

def filter_data_for_last_n_weeks(df, num_weeks=4, days_to_allow_for_time_approval=2):
    """
    Filters the weekly DataFrame to include only data from the most recent N weeks,
    using an ending week that is 'days_to_allow_for_time_approval' days before the latest week in the dataset.
    """
    if df.empty or 'WeekStart' not in df.columns:
        print("WARNING: Input DataFrame is empty or missing 'WeekStart' column for filtering.")
        return pd.DataFrame() # Return empty DataFrame if no data or no WeekStart column

    max_week = df['WeekStart'].max()
    effective_end_week = max_week - timedelta(days=days_to_allow_for_time_approval)
    start_week_for_n_weeks = effective_end_week - timedelta(weeks=num_weeks) + timedelta(days=1)
    df_filtered = df[(df['WeekStart'] >= start_week_for_n_weeks) & (df['WeekStart'] <= effective_end_week)].copy()
    df_filtered = df_filtered.sort_values('WeekStart')
    print(f"Data filtered for the last {num_weeks} weeks (from {start_week_for_n_weeks.strftime('%m/%d/%Y')} to {effective_end_week.strftime('%m/%d/%Y')}).")
    return df_filtered



def descriptive_stats_by_role_facility(df, model_hours_df=None, census_df=None):
    """
    For each Facility-Role combination, compute and display descriptive statistics:
    mean, median, vMean, vMedian, range, MADm, std, IQR, skewness, kurtosis, Model Hours, Census, ExptdHrs, varExpected.
    vMean and vMedian are percent deviations from Model Hours (negative if under Model Hours).
    ExptdHrs = get_peer_hours(df, census_df, facility, role), varExpected = 100 * (mean - ExptdHrs) / ExptdHrs (if ExptdHrs != 0).
    Operates on weekly data.
    """
    results = []
    grouped = df.groupby(['Facility', 'Role'])
    for (facility, role), group in grouped:
        actual_hours = group['ActualHours'].dropna()
        n = len(actual_hours)
        if n == 0:
            results.append(['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', ''])
            continue
        mean = actual_hours.mean()
        median = actual_hours.median()
        # Model Hours lookup (sum for the week)
        model_hours = None
        if model_hours_df is not None:
            if not isinstance(model_hours_df, pd.DataFrame):
                raise ValueError("model_hours_df must be a pandas DataFrame.")
            match = model_hours_df[(model_hours_df['Facility'] == facility) & (model_hours_df['Role'] == role)]
            if not match.empty:
                model_hours = match.iloc[0]['ModelHours']
        # Census lookup
        census = ''
        if census_df is not None:
            if not isinstance(census_df, pd.DataFrame):
                raise ValueError("census_df must be a pandas DataFrame.")
            match = census_df[census_df['Facility'] == facility]
            if not match.empty:
                census = match.iloc[0]['Census']
        # Hours for this role at other facilities and variance from that. 
        peer_hours = get_peer_hours(df, census_df, facility, role) if census_df is not None else ''
        var_peer_hours = ''
        if peer_hours not in ('', 0, None):
            var_peer_hours_val = 100 * (median - peer_hours) / peer_hours
            var_peer_hours = pct_fmt(var_peer_hours_val)
        # vMean and vMedian: percent deviation from Model Hours
        if model_hours is not None and model_hours != 0:
            var_mean_val = 100 * (mean - model_hours) / model_hours
            var_median_val = 100 * (median - model_hours) / model_hours
            var_mean = pct_fmt(var_mean_val)
            var_median = pct_fmt(var_median_val)
        else:
            var_mean = ''
            var_median = ''
        # Descriptive statistics
        min_val = actual_hours.min()
        max_val = actual_hours.max()
        data_range = max_val - min_val
        madm = np.median(np.abs(actual_hours - median))
        std = actual_hours.std()
        q75, q25 = np.percentile(actual_hours, [75, 25])
        iqr = q75 - q25
        skew = actual_hours.skew()
        if data_range == 0:
            kurt = None
        else:
            kurt = actual_hours.kurtosis() - 3
        normality = normality_test(actual_hours)
        kurt_display = f"{kurt:.2f}" if kurt is not None else ''
        results.append([
            facility, census, role, n, normality, model_hours if model_hours is not None else '',
            f"{peer_hours:.2f}" if peer_hours not in ('', None) else '',
            f"{var_peer_hours}" if var_peer_hours != '' else '',
            f"{mean:.2f}", var_mean,
            f"{median:.2f}", var_median,
            f"{data_range:.2f}", f"{madm:.2f}", f"{std:.2f}", f"{iqr:.2f}", f"{skew:.2f}", kurt_display
        ])
    header_cols = ['Facility', 'Census', 'Role', 'n', 'Normal', 'ModelHrs', 'PeerHrs', 'vPeerHrs', 'Mean', 'vMean%', 'Median', 'vMedian%', 'Range', 'MedAD', 'Std', 'IQR', 'Skew', 'Kurtosis']    
    results_df = pd.DataFrame(results, columns=header_cols)
    return results_df

def normality_test(actual_hours):
    """
    Performs a normality test (Shapiro-Wilk) on a pandas Series of values.
    Returns 'Lacks Data' if n < 5, 'Zero Range' if all values are identical, 'True' if normal, 'False' if not.
    """
    n = len(actual_hours)
    data_range = actual_hours.max() - actual_hours.min() if n > 0 else 0
    if n < 5:
        return 'Lacks Data'
    elif data_range == 0:
        return 'Zero Range'
    else:
        W, p_value = shapiro(actual_hours)
        return 'True' if p_value > 0.05 else 'False'
    
def get_peer_hours(df, census_df, facility, position):
    """
    For a given facility and position (role), return the normalized expected hours for that position
    from all other facilities (i.e., the peer median normalized hours * this facility's census).
    Returns a float (expected peer hours for this facility/position) or None if not computable.
    """
    if not isinstance(census_df, pd.DataFrame):
        raise ValueError("census_df must be a pandas DataFrame.")
    merged = df.merge(census_df, on='Facility', how='left')
    filtered = merged[merged['Role'] == position].copy()
    # Get this facility's census
    this_census = census_df[census_df['Facility'] == facility]['Census']
    if this_census.empty or this_census.iloc[0] in ('', 0, None):
        return None
    census = this_census.iloc[0]
    # Peer median normalized hours (exclude this facility)
    peer_groups = filtered[filtered['Facility'] != facility]
    if peer_groups.empty:
        return None
    peer_normalized_hours = peer_groups.groupby('Facility').apply(
        lambda g: g['ActualHours'].median() / g['Census'].iloc[0] if g['Census'].iloc[0] else np.nan
    ).dropna()
    if peer_normalized_hours.empty:
        return None
    peer_normalized_median = peer_normalized_hours.median()
    peer_expected_hours = peer_normalized_median * census
    return peer_expected_hours


def output_console_descriptive_stats_table(result_df):
    """
    Print the descriptive statistics DataFrame in a formatted console table (weekly data).
    """
    header_cols = ['Facility', 'Census', 'Role', 'n', 'Normal', 'ModelHrs', 'PeerHrs', 'vPeerHrs', 'Mean', 'vMean%', 'Median', 'vMedian%', 'Range', 'MedAD', 'Std', 'IQR', 'Skew', 'Kurtosis']    
    col_widths = [15, 6, 25, 5, 10, 10, 10, 12, 8, 10, 8, 10, 8, 8, 8, 8, 8, 10]
    alignments = ['<', '>', '<', '>', '>', '>', '>', '>', '>', '>', '>', '>', '>', '>', '>', '>', '>', '>']
    header_fmt = f'{{:{alignments[0]}{col_widths[0]}}}' + ''.join([f' {{:{a}{w}}}' for a, w in zip(alignments[1:], col_widths[1:])])
    print("WEEKLY DESCRIPTIVE STATISTICS TABLE:")
    print(header_fmt.format(*header_cols))
    print("-" * (sum(col_widths) + len(col_widths) - 1))
    for _, row in result_df.iterrows():
        row_display = [str(val)[:w] if val is not None else '' for val, w in zip(row, col_widths)]
        print(header_fmt.format(*row_display))
    print("-" * (sum(col_widths) + len(col_widths) - 1) + "\n")


def output_csv_descriptive_stats_table(result_df, filename):
    """
    Write the descriptive statistics DataFrame to a CSV file.
    """
    result_df.to_csv(filename, index=False)

def load_static_census(file_path="static_census.csv"):
    """
    Loads the static census information from a CSV file and returns a clean DataFrame.
    Ensures required columns, strips whitespace, and enforces correct types.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Census file not found: {file_path}")
    df = pd.read_csv(file_path)
    
    # Required columns
    required_cols = ['Facility', 'Census']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing expected columns in the census file: {', '.join(missing_cols)}")
    
    # Strip whitespace from column names and Facility values
    df.columns = df.columns.str.strip()
    df['Facility'] = df['Facility'].astype(str).str.strip()
    
    # Ensure Census is numeric
    df['Census'] = pd.to_numeric(df['Census'], errors='coerce')
    if df['Census'].isnull().any():
        raise ValueError("Non-numeric values found in 'Census' column.")
    
    return df

def output_console_violations_summary_table(violations_summary):
    """
    Print the violations summary dictionary in a formatted console table (weekly data).
    """
    header_cols = [
        'Facility_Role', 'Has Violations', 'Control Limit Calc Start', 'Control Limit Calc End'
    ]
    col_widths = [30, 15, 25, 25]
    alignments = ['<', '>', '>', '>']
    header_fmt = f'{{:{alignments[0]}{col_widths[0]}}}' + ''.join([f' {{:{a}{w}}}' for a, w in zip(alignments[1:], col_widths[1:])])
    print("WEEKLY VIOLATIONS SUMMARY TABLE:")
    print(header_fmt.format(*header_cols))
    print("-" * (sum(col_widths) + len(col_widths) - 1))
    for key, val in violations_summary.items():
        row = [
            key,
            str(val.get('has_violations', '')),
            val.get('control_limit_calc_start_date', ''),
            val.get('control_limit_calc_end_date', '')
        ]
        row_display = [str(v)[:w] if v is not None else '' for v, w in zip(row, col_widths)]
        print(header_fmt.format(*row_display))
    print("-" * (sum(col_widths) + len(col_widths) - 1) + "\n")


def centralized_violation_detection(df_filtered_for_chart_display, control_limits, control_limit_calc_start_date, 
                                    control_limit_calc_end_date):
    """
    Detects control violations for all Facility-Role combinations based on control limits.
    Returns a summary dictionary for all violations. Operates on weekly data.
    """
    all_violations_summary = {}
    for limit_key in control_limits.keys():
        facility, role = limit_key.split('_', 1)
        subset_df_for_analysis = df_filtered_for_chart_display[(df_filtered_for_chart_display['Facility'] == facility) & (df_filtered_for_chart_display['Role'] == role)]
        limits = control_limits[limit_key]
        mean_line = limits['mean']
        ucl_line = limits['ucl']
        lcl_line = limits['lcl']
        violations_in_reporting_range = []
        has_violations = False
        #if not subset_df_for_analysis.empty:
        # Look up model hours for this facility-role
        model_hours = None
        if 'ModelHours' in subset_df_for_analysis.columns and not subset_df_for_analysis.empty:
            model_hours = subset_df_for_analysis['ModelHours'].iloc[0]
        violations_in_reporting_range = detect_control_violations(subset_df_for_analysis, mean_line, ucl_line, lcl_line, model_hours)
        has_violations = bool(violations_in_reporting_range)
        all_violations_summary[limit_key] = {
            'violations_in_reporting_range': violations_in_reporting_range,
            'has_violations': has_violations,
            'control_limit_calc_start_date': control_limit_calc_start_date,
            'control_limit_calc_end_date': control_limit_calc_end_date
        }
    print("CENTRALIZED ANALYSIS: Violation detection completed (weekly data).")
    return all_violations_summary

def output_console_control_limits_table(control_limits):
    """
    Print the control limits dictionary in a formatted console table (weekly data).
    """
    header_cols = [
        'Facility_Role', 'Mean/Median', 'UCL', 'LCL', 'Std/MAD', 'Method'
    ]
    col_widths = [30, 12, 12, 12, 12, 10]
    alignments = ['<', '>', '>', '>', '>', '<']
    header_fmt = f'{{:{alignments[0]}{col_widths[0]}}}' + ''.join([f' {{:{a}{w}}}' for a, w in zip(alignments[1:], col_widths[1:])])
    print("WEEKLY CONTROL LIMITS TABLE:")
    print(header_fmt.format(*header_cols))
    print("-" * (sum(col_widths) + len(col_widths) - 1))
    for key, val in control_limits.items():
        row = [
            key,
            f"{val.get('mean', ''):.2f}",
            f"{val.get('ucl', ''):.2f}",
            f"{val.get('lcl', ''):.2f}",
            f"{val.get('std', ''):.2f}",
            val.get('method', '')
        ]
        row_display = [str(v)[:w] if v is not None else '' for v, w in zip(row, col_widths)]
        print(header_fmt.format(*row_display))
    print("-" * (sum(col_widths) + len(col_widths) - 1) + "\n")