## FEATURE:

The application ingests model hours (what should be worked) and clock hours (what was actually worked) for every facility, compares them, detects statistically significant variances, and publishes per-facility PDF reports that show only the exceptions. Phase 1 is batch/off-line; Phase 2 will add a real-time interactive HTML layer.

- F-0   Control Variables - These are the variables that I would like to have established as constants to use as indicators, etc., within the program to be able to do control runs.

    - F-0a  Days to Drop - The number of days in the data does not consider working from the oldest date back.
    - F-0b  Days to Process - The number of days to look back from the given period end date.
    - F-0c  New Data Day - The day of the week to consider having clean data.
    - F-0d  Use Data Day - A true/false variable indicating whether the new day-to-day should be used. When this variable is false, the "days to drop" value is used. When this variable is true, the "days to drop" is used to calculate how many of the new data days to go back and drop from.
    - F-0e  Use Statistics - A true/false value indicating whether statistical abnormality detection should be reported.
    - F-0f  Allows Variance From Model - A percentage value indicating how far off the model a value can be before it is flagged as an exception.
    - F-0g  Weeks for Control - An integer value indicating how many weeks to consider when using historic data to establish control limits.
    - F-0g  Weeks For Trends - An integer value indicating how many weeks to consider when looking for trends.
    - F-0h  Director Setup  - Please include the code and variables necessary to define the various paths that we will need, such as the input files, where the output files will go, where the settings files might live, etc.

- F-1   Model ingestion  - Load the model data from the sample model data file found in \input\SampleModelData.csv

    - F-1a  Display model - Display a table-formatted version of the model to the console.

- F-2   Hours ingestion  - Load the facility data from the sample facility data file found in \input\SampleModelData.csv Noting that the facility data file may contain data for multiple facilities, each of which can be separated by the facility location key.

- F-2	Data normalization - Standardize date/time using MMDDYYYY as the preferred format for the project, convert hours to float, harmonize role names (case, spelling).

- F-3	Variance Detection - When performing each of the calculations in this section, include an indicator with the returned data to show whether the given item was an exception to the rules.
        
    - F-3a  For each Role × Day × Facility Combination. Calculate the descriptive statistics that will be important for this project and include the model hours for that combination for further use below. Test the data for normality. For the descriptive statistics, calculate at least the mean, median, standard deviation, upper control limit, and lower control limit using both the standard deviation and median absolute deviation methods. Using the descriptive statistics and the model data, flag any combination that differs from the model by more than the percentage specified in the control values. If the control value for using statistics is true, then flag any value that is outside of its standard deviation if the data is normal, or outside of its mean absolute deviation if the data is not normal. When using statistics to identify exceptions, also include the ability to look for trends that may indicate exceptions.
    
    - F-3b  For each Employee x Role at the facility, calculate the descriptive statistics to analyze their hours at the facility. Test the data for normality. For the descriptive statistics, calculate at least the mean, median, standard deviation, upper control limit, and lower control limit using both the standard deviation and median absolute deviation methods. Using the descriptive statistics and the model data, flag any combination that differs from the model by more than the percentage specified in the control values. If the control value for using statistics is true, then flag any value that is outside of its standard deviation if the data is normal, or outside of its mean absolute deviation if the data is not normal. When using statistics to identify exceptions, also include the ability to look for trends that may indicate exceptions.
    
- F-4	Trend analysis  - Trailing window per facility/role with linear regression slope & p-value.

- F-5 	Exception compiler - Aggregate flags into a tidy “exceptions” DataFrame ready for reporting.

- F-6	PDF report generator - One PDF per facility containing: 

    - F-6a  Cover page with date range
    - F-6b  KPI summary table
    - F-6c  Variance heat-map & trend charts
    - F-6d  Detailed exception list.

- F-7   Logging - Please include reasonable logging and exit codes throughout the application to enable and support troubleshooting.

- F-8   Error Handling - Please include reasonable error handling throughout the application to support troubleshooting.

## DESIRED PACKAGE USAGE

I would prefer to use the packages below to accomplish the goals of the program period. If there are additional packages necessary, please note and include them.

- Statistics: pandas, scipy, numpy, matplotlib, seaborn
- PDF Generation: pyppeteer
- Utility: asyncio

## EXAMPLES:

In the `examples/` folder, there are a few sample Python files from another project that was similar to this in nature and may be useful to you as an example. You do not need to copy from these examples directly, but please use them as inspiration for what I believe needs to be done similarly in this project.

Also in the `examples/` folder, are the sample model data and sample hours data input files that you can use to assess how to build the ingestion routines.

- `examples/cli.py` - use this as a template to create the CLI
- `examples/agent/` - read through all of the files here to understand best practices for creating Pydantic AI agents that support different providers and LLMs, handling agent dependencies, and adding tools to the agent.

Don't copy any of these examples directly, it is for a different project entirely. But use this as inspiration and for best practices.

## OTHER CONSIDERATIONS:

- Include a .env.example, README with instructions for setup including how to configure the basics.
- Include the project structure in the README.
- Virtual environment has already been set up with the necessary dependencies.
- Use python_dotenv and load_env() for environment variables