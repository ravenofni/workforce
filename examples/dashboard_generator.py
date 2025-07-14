import asyncio
import os
import pandas as pd
import matplotlib.pyplot as plt 
import seaborn as sns          
from datetime import timedelta
from debugging_tools import get_weekly_actual_hours_for_role, print_weekly_actual_hours_table

# Import functions from our new modules

from data_processing import (load_and_preprocess_data, calculate_control_limits, filter_data_for_last_n_weeks,
    descriptive_stats_by_role_facility, normality_test, output_console_descriptive_stats_table, load_static_census,
    centralized_violation_detection, output_console_violations_summary_table, output_console_control_limits_table)
from chart_creation import generate_individual_charts_for_facility, generate_individual_facility_reports
from report_assembly import build_full_report_html, detect_control_violations 
from pdf_export import convert_html_to_pdf
from corporate_report import generate_corporate_report 

# --- Testing Modifiers ---
TEST_MODE = False 
GENERATE_ONLY_EXCEPTIONS = False
MAX_FACILITIES = 1
MAX_ROLES = 1


# --- Global Configuration ---
REPORTING_RANGE_WEEKS = 12  # Show up to 12 weeks in reporting
CONTROL_LIMIT_CALC_WEEKS = 12  # Use up to 24 weeks for control limit calculation
DAYS_TO_ALLOW_FOR_TIME_APPROVAL = 2  # Number of days to cull from input data due to time entry not being fully approved.


# --- Directory Setup ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_PATH = os.path.join(SCRIPT_DIR, "input/samplefull.csv")
CENSUS_FILE_PATH = os.path.join(SCRIPT_DIR, "settings/static_census.csv")
GRAPHS_ROOT_SUBFOLDER = "graphs"
REPORTS_SUBFOLDER = "reports"
BASE_OUTPUT_DIR = os.path.join(SCRIPT_DIR, GRAPHS_ROOT_SUBFOLDER)
HTML_REPORT_DIR = os.path.join(BASE_OUTPUT_DIR, REPORTS_SUBFOLDER)

# Create necessary base directories
os.makedirs(BASE_OUTPUT_DIR, exist_ok=True)
os.makedirs(HTML_REPORT_DIR, exist_ok=True)

# --- Load visible cost centers and friendly names from config file ---
VISIBLE_COST_CENTERS_FILE = os.path.join(SCRIPT_DIR, "visible_cost_centers.config")
VISIBLE_COST_CENTERS = []
COST_CENTER_FRIENDLY_NAMES = {}
with open(VISIBLE_COST_CENTERS_FILE, 'r') as f:
    for line in f:
        parts = line.strip().split(',')
        if len(parts) >= 3:
            cost_center = parts[0].strip()
            visible = parts[1].strip().lower()
            friendly_name = ','.join(parts[2:]).strip()  # In case friendly name contains commas
            COST_CENTER_FRIENDLY_NAMES[cost_center] = friendly_name
            if visible == 'true':
                VISIBLE_COST_CENTERS.append(cost_center)




async def main():
    
    report_display_start_date = "N/A" 
    report_display_end_date = "N/A"   

    try:


        #Load data from the input file into df, and build the model hours df at the same time.
        df, model_hours_df = load_and_preprocess_data(FILE_PATH)
        



        if TEST_MODE: # Limit to first MAX_FACILITIES facilities and first MAX_ROLES roles
            facilities = df['Facility'].drop_duplicates().head(MAX_FACILITIES)
            roles = df['Role'].drop_duplicates().head(MAX_ROLES)
            df = df[df['Facility'].isin(facilities) & df['Role'].isin(roles)]
            print(f"TEST_MODE: Limiting analysis to a maximum of {MAX_FACILITIES} facilities and {MAX_ROLES} roles.")
            print(f"TEST_MODE: Data contains {len(facilities)} facilities and {len(roles)} roles.")
            
        #Example usage (uncomment to use in your script):
        #weekly_hours = print_weekly_actual_hours_table(df, 'Ansley Park', 'Hskpg. Suprv.')
       


        # Load static census information
        census_df = None
        try:            
            census_df = load_static_census(CENSUS_FILE_PATH)
        except Exception as e:
            print(f"WARNING: Could not load census file: {e}")



        # Setup the filtered DataFrame for various uses:
        # CONTROL_LIMIT_CALC_WEEKS => the number of weeks to use for control limit calculation.
        # DAYS_TO_ALLOW_FOR_TIME_APPROVAL => the number of days to cull from input data due to time entry not being fully approved.
        # REPORTING_RANGE_WEEKS => the number of weeks to filter data for chart display and violation detection.        
        # Normality is also handled internally in the calculate_control_limits function.
        most_recent_week_in_df = df['WeekStart'].max()
        effective_end_week = most_recent_week_in_df - timedelta(days=DAYS_TO_ALLOW_FOR_TIME_APPROVAL)
        control_effective_start_week = effective_end_week - timedelta(weeks=CONTROL_LIMIT_CALC_WEEKS) + timedelta(days=1)
        reporting_effective_start_week = effective_end_week - timedelta(weeks=REPORTING_RANGE_WEEKS) + timedelta(days=1)

        df_for_control_limits = df[(df['WeekStart'] >= control_effective_start_week) & (df['WeekStart'] <= effective_end_week)].copy()
        df_for_reporting = df[(df['WeekStart'] >= reporting_effective_start_week) & (df['WeekStart'] <= effective_end_week)].copy()

        

        

        # Statistical Analyses        
        descriptive_results = descriptive_stats_by_role_facility(df_for_reporting, model_hours_df, census_df)        
        output_console_descriptive_stats_table(descriptive_results)
        
        
        # Calculate control limits (normality is handled internally)
        control_limits = calculate_control_limits(df_for_control_limits)
        output_console_control_limits_table(control_limits)
        
        test = 1 



        # Test for violations of the control limits
        print("Violation Detections: Checking for control limit violations for all Facility-Role ... ")
        all_violations_summary = centralized_violation_detection(
            df_for_reporting,
            control_limits,
            control_effective_start_week,
            effective_end_week            
        )
        output_console_violations_summary_table(all_violations_summary)

        test = 1

    # #--- BEGIN CENTRALIZED VIOLATION DETECTION ---
    #     #control_limit_calc_start_date = df_for_limits['Date'].min().strftime('%m/%d/%Y') if not df_for_limits.empty else 'N/A'
    #     #control_limit_calc_end_date = df_for_limits['Date'].max().strftime('%m/%d/%Y') if not df_for_limits.empty else 'N/A'

        

    #     # # Filter data for chart display
    #     df_filtered_for_chart_display = filter_data_for_last_n_weeks(df, num_weeks=MID_RANGE_WEEKS, days_to_allow_for_time_approval=DAYS_TO_ALLOW_FOR_TIME_APPROVAL)

        if not df_for_reporting.empty:
             report_display_start_date = df_for_reporting['WeekStart'].min().strftime('%m/%d/%Y')
             report_display_end_date = df_for_reporting['WeekStart'].max().strftime('%m/%d/%Y')
        else:
             print("WARNING: Filtered DataFrame for chart display is empty. Report display dates will be N/A.")

    #     plt.rcParams['figure.facecolor'] = 'white'
    #     plt.rcParams['axes.facecolor'] = 'white'

    #     print("\nSkipping combined chart generation (not practical for large datasets and individual reports suffice).")


        


        # Step 4: Iterate through facilities to generate individual charts and reports
        await generate_individual_facility_reports(
            df_for_reporting,  # Use the correct DataFrame for chart display
            control_limits,
            model_hours_df,
            BASE_OUTPUT_DIR,
            HTML_REPORT_DIR,
            GENERATE_ONLY_EXCEPTIONS,
            TEST_MODE,
            MAX_FACILITIES,
            MAX_ROLES,            
            all_violations_summary,
            control_effective_start_week,
            effective_end_week,
            report_display_start_date,
            report_display_end_date,
            VISIBLE_COST_CENTERS
        )
        #End Step 4



    except Exception as e:
        print(f"An error occurred while loading, visualizing, or generating the report: {e}")

print("\nProcess completed.")


if __name__ == "__main__":
    asyncio.run(main())







