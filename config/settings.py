"""
Configuration settings for the workforce analytics system.
Implements F-0 Control Variables as specified in INITIAL.md.
"""

import os
from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class ControlVariables(BaseModel):
    """Control variables for workforce analytics (F-0)"""
    
    # F-0a: Days to Drop - The number of days in the data does not consider working from the oldest date back
    days_to_drop: int = Field(
        default=int(os.getenv("DAYS_TO_DROP", "7")),
        description="F-0a: Days to drop from oldest date back"
    )
    
    # F-0b: Days to Process - The number of days to look back from the given period end date
    days_to_process: int = Field(
        default=int(os.getenv("DAYS_TO_PROCESS", "84")),
        description="F-0b: Days to look back from period end date"
    )
    
    # F-0c: New Data Day - The day of the week to consider having clean data
    new_data_day: int = Field(
        default=int(os.getenv("NEW_DATA_DAY", "1")),
        description="F-0c: Day of week for clean data (1=Monday, 7=Sunday)"
    )
    
    # F-0d: Use Data Day - A true/false variable indicating whether the new day-to-day should be used
    use_data_day: bool = Field(
        default=os.getenv("USE_DATA_DAY", "true").lower() == "true",
        description="F-0d: Use new data day vs days to drop"
    )
    
    # F-0e: Use Statistics - A true/false value indicating whether statistical abnormality detection should be reported
    use_statistics: bool = Field(
        default=os.getenv("USE_STATISTICS", "true").lower() == "true",
        description="F-0e: Enable statistical abnormality detection"
    )
    
    # F-0f: Allows Variance From Model - A percentage value indicating how far off the model a value can be before it is flagged as an exception
    variance_threshold: float = Field(
        default=float(os.getenv("VARIANCE_THRESHOLD", "15.0")),
        description="F-0f: Variance percentage from model before flagging exception",
        ge=0.0,
        le=100.0
    )
    
    # F-0g: Weeks for Control - An integer value indicating how many weeks to consider when using historic data to establish control limits
    weeks_for_control: int = Field(
        default=int(os.getenv("WEEKS_FOR_CONTROL", "12")),
        description="F-0g: Weeks for control limit calculation",
        ge=1
    )
    
    # F-0g: Weeks For Trends - An integer value indicating how many weeks to consider when looking for trends
    weeks_for_trends: int = Field(
        default=int(os.getenv("WEEKS_FOR_TRENDS", "8")),
        description="F-0g: Weeks for trend analysis",
        ge=1
    )


class DirectorySettings(BaseModel):
    """Directory path configuration following examples patterns"""
    
    # F-0h: Director Setup - Define various paths needed
    script_dir: str = Field(default_factory=lambda: os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Input directories  
    input_dir: str = Field(default="input")
    examples_dir: str = Field(default="examples")
    
    # Output directories
    output_dir: str = Field(default="output")
    reports_dir: str = Field(default="output/reports")
    logs_dir: str = Field(default="logs")
    
    # Configuration directories
    settings_dir: str = Field(default="config")
    
    def model_post_init(self, __context=None) -> None:
        """Initialize relative paths after script_dir is set"""
        if not os.path.isabs(self.input_dir):
            self.input_dir = os.path.join(self.script_dir, self.input_dir)
        if not os.path.isabs(self.examples_dir):
            self.examples_dir = os.path.join(self.script_dir, self.examples_dir)
        if not os.path.isabs(self.output_dir):
            self.output_dir = os.path.join(self.script_dir, self.output_dir)
        if not os.path.isabs(self.reports_dir):
            self.reports_dir = os.path.join(self.script_dir, self.reports_dir)
        if not os.path.isabs(self.logs_dir):
            self.logs_dir = os.path.join(self.script_dir, self.logs_dir)
        if not os.path.isabs(self.settings_dir):
            self.settings_dir = os.path.join(self.script_dir, self.settings_dir)


class AppSettings(BaseModel):
    """Main application settings combining all configuration"""
    
    control_variables: ControlVariables = Field(default_factory=ControlVariables)
    directories: DirectorySettings = Field(default_factory=DirectorySettings)
    
    # Additional application settings
    log_level: str = Field(
        default=os.getenv("LOG_LEVEL", "INFO"),
        description="Logging level for the application"
    )
    
    generate_only_exceptions: bool = Field(
        default=os.getenv("GENERATE_ONLY_EXCEPTIONS", "false").lower() == "true",
        description="Generate reports only for facilities with exceptions"
    )
    
    max_sample_size_normality: int = Field(
        default=5000,
        description="Maximum sample size for normality testing (scipy limitation)"
    )
    
    pdf_timeout_seconds: int = Field(
        default=60,
        description="Timeout for PDF generation operations"
    )


def get_settings() -> AppSettings:
    """Get application settings instance"""
    return AppSettings()


def ensure_directories(settings: AppSettings) -> None:
    """Ensure all required directories exist"""
    directories = [
        settings.directories.input_dir,
        settings.directories.output_dir,
        settings.directories.reports_dir,
        settings.directories.logs_dir,
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)