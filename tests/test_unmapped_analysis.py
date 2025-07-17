"""
Unit tests for unmapped hours analysis module.
Tests unmapped hours detection, aggregation, and summary statistics.
"""

import pytest
import pandas as pd
from datetime import datetime
from src.analysis.unmapped_analysis import (
    is_unmapped_role,
    extract_unmapped_hours_data,
    aggregate_unmapped_by_category_and_employee,
    calculate_unmapped_summary_stats,
    analyze_unmapped_hours_for_facility,
    format_unmapped_hours_for_display
)
from src.models.data_models import UnmappedHoursResult, UnmappedCategorySummary


class TestUnmappedRoleDetection:
    """Test unmapped role detection functionality."""
    
    def test_is_unmapped_role_with_unmapped_nursing(self):
        """Test detection of unmapped nursing roles."""
        assert is_unmapped_role("Unmapped Nursing") == True
        assert is_unmapped_role("unmapped nursing") == True
        assert is_unmapped_role("UNMAPPED NURSING") == True
    
    def test_is_unmapped_role_with_unmapped_dietary(self):
        """Test detection of unmapped dietary roles."""
        assert is_unmapped_role("Unmapped Dietary") == True
        assert is_unmapped_role("unmapped dietary") == True
    
    def test_is_unmapped_role_with_other_unmapped(self):
        """Test detection of other unmapped category."""
        assert is_unmapped_role("Other Unmapped") == True
        assert is_unmapped_role("other unmapped") == True
    
    def test_is_unmapped_role_with_regular_roles(self):
        """Test that regular roles are not detected as unmapped."""
        assert is_unmapped_role("RN") == False
        assert is_unmapped_role("CNA") == False
        assert is_unmapped_role("Nursing Manager") == False
        assert is_unmapped_role("Dietary Aide") == False
    
    def test_is_unmapped_role_edge_cases(self):
        """Test edge cases for unmapped role detection."""
        assert is_unmapped_role("") == False
        assert is_unmapped_role("Mapped Role") == False
        assert is_unmapped_role("UnmappedNursing") == False  # No space


class TestUnmappedDataExtraction:
    """Test unmapped hours data extraction functionality."""
    
    @pytest.fixture
    def sample_facility_data(self):
        """Create sample facility data for testing."""
        data = {
            'Facility': ['Test Facility', 'Test Facility', 'Test Facility', 'Test Facility', 'Other Facility'],
            'Role': ['Unmapped Nursing', 'RN', 'Unmapped Dietary', 'CNA', 'Unmapped Nursing'],
            'Date': [
                datetime(2025, 1, 1),
                datetime(2025, 1, 1),
                datetime(2025, 1, 2),
                datetime(2025, 1, 2),
                datetime(2025, 1, 1)
            ],
            'ActualHours': [8.0, 12.0, 4.0, 8.0, 6.0],
            'EmployeeID': ['EMP001', 'EMP002', 'EMP003', 'EMP004', 'EMP005'],
            'EmployeeName': ['John Doe', 'Jane Smith', 'Bob Johnson', 'Alice Brown', 'Charlie Wilson']
        }
        return pd.DataFrame(data)
    
    def test_extract_unmapped_hours_data_success(self, sample_facility_data):
        """Test successful extraction of unmapped hours data."""
        start_date = datetime(2025, 1, 1)
        end_date = datetime(2025, 1, 2)
        
        result = extract_unmapped_hours_data(
            sample_facility_data, 'Test Facility', start_date, end_date
        )
        
        assert len(result) == 2  # Should get 2 unmapped entries
        assert all(result['Role'].isin(['Unmapped Nursing', 'Unmapped Dietary']))
        assert all(result['Facility'] == 'Test Facility')
    
    def test_extract_unmapped_hours_data_no_facility_match(self, sample_facility_data):
        """Test extraction with non-existent facility."""
        start_date = datetime(2025, 1, 1)
        end_date = datetime(2025, 1, 2)
        
        result = extract_unmapped_hours_data(
            sample_facility_data, 'Nonexistent Facility', start_date, end_date
        )
        
        assert len(result) == 0
    
    def test_extract_unmapped_hours_data_no_unmapped_roles(self):
        """Test extraction with data containing no unmapped roles."""
        data = {
            'Facility': ['Test Facility', 'Test Facility'],
            'Role': ['RN', 'CNA'],
            'Date': [datetime(2025, 1, 1), datetime(2025, 1, 1)],
            'ActualHours': [8.0, 8.0],
            'EmployeeID': ['EMP001', 'EMP002'],
            'EmployeeName': ['John Doe', 'Jane Smith']
        }
        df = pd.DataFrame(data)
        
        start_date = datetime(2025, 1, 1)
        end_date = datetime(2025, 1, 2)
        
        result = extract_unmapped_hours_data(df, 'Test Facility', start_date, end_date)
        
        assert len(result) == 0


class TestUnmappedAggregation:
    """Test unmapped hours aggregation functionality."""
    
    @pytest.fixture
    def sample_unmapped_data(self):
        """Create sample unmapped data for testing."""
        data = {
            'Role': ['Unmapped Nursing', 'Unmapped Nursing', 'Unmapped Dietary', 'Unmapped Nursing'],
            'EmployeeID': ['EMP001', 'EMP001', 'EMP003', 'EMP002'],
            'EmployeeName': ['John Doe', 'John Doe', 'Bob Johnson', 'Jane Smith'],
            'ActualHours': [8.0, 4.0, 6.0, 10.0]
        }
        return pd.DataFrame(data)
    
    def test_aggregate_unmapped_by_category_and_employee(self, sample_unmapped_data):
        """Test aggregation of unmapped hours by category and employee."""
        facility = 'Test Facility'
        start_date = datetime(2025, 1, 1)
        end_date = datetime(2025, 1, 2)
        
        results = aggregate_unmapped_by_category_and_employee(
            sample_unmapped_data, facility, start_date, end_date
        )
        
        assert len(results) == 3  # 3 unique employee-category combinations
        
        # Check that John Doe's nursing hours are aggregated (8.0 + 4.0 = 12.0)
        john_nursing = next((r for r in results if r.employee_name == 'John Doe' and r.category == 'Unmapped Nursing'), None)
        assert john_nursing is not None
        assert john_nursing.total_hours == 12.0
        
        # Check percentage calculations
        total_nursing_hours = 12.0 + 10.0  # John + Jane
        expected_john_percentage = (12.0 / total_nursing_hours) * 100
        assert abs(john_nursing.percentage_of_category - expected_john_percentage) < 0.01
    
    def test_aggregate_unmapped_by_category_and_employee_empty_data(self):
        """Test aggregation with empty data."""
        empty_df = pd.DataFrame()
        facility = 'Test Facility'
        start_date = datetime(2025, 1, 1)
        end_date = datetime(2025, 1, 2)
        
        results = aggregate_unmapped_by_category_and_employee(
            empty_df, facility, start_date, end_date
        )
        
        assert len(results) == 0


class TestUnmappedSummaryStats:
    """Test unmapped summary statistics calculation."""
    
    @pytest.fixture
    def sample_unmapped_results(self):
        """Create sample unmapped results for testing."""
        return [
            UnmappedHoursResult(
                facility='Test Facility',
                category='Unmapped Nursing',
                employee_name='John Doe',
                employee_id='EMP001',
                total_hours=12.0,
                percentage_of_category=60.0,
                analysis_period_start=datetime(2025, 1, 1),
                analysis_period_end=datetime(2025, 1, 2)
            ),
            UnmappedHoursResult(
                facility='Test Facility',
                category='Unmapped Nursing',
                employee_name='Jane Smith',
                employee_id='EMP002',
                total_hours=8.0,
                percentage_of_category=40.0,
                analysis_period_start=datetime(2025, 1, 1),
                analysis_period_end=datetime(2025, 1, 2)
            ),
            UnmappedHoursResult(
                facility='Test Facility',
                category='Unmapped Dietary',
                employee_name='Bob Johnson',
                employee_id='EMP003',
                total_hours=6.0,
                percentage_of_category=100.0,
                analysis_period_start=datetime(2025, 1, 1),
                analysis_period_end=datetime(2025, 1, 2)
            )
        ]
    
    def test_calculate_unmapped_summary_stats(self, sample_unmapped_results):
        """Test calculation of summary statistics."""
        facility = 'Test Facility'
        start_date = datetime(2025, 1, 1)
        end_date = datetime(2025, 1, 2)
        
        summaries = calculate_unmapped_summary_stats(
            sample_unmapped_results, facility, start_date, end_date
        )
        
        assert len(summaries) == 2  # 2 categories
        
        # Find nursing summary
        nursing_summary = next((s for s in summaries if s.category == 'Unmapped Nursing'), None)
        assert nursing_summary is not None
        assert nursing_summary.total_hours == 20.0  # 12.0 + 8.0
        assert nursing_summary.employee_count == 2
        assert nursing_summary.average_hours_per_employee == 10.0
        
        # Check percentage of total unmapped (20 out of 26 total)
        expected_percentage = (20.0 / 26.0) * 100
        assert abs(nursing_summary.percentage_of_total_unmapped - expected_percentage) < 0.01
    
    def test_calculate_unmapped_summary_stats_empty_results(self):
        """Test summary calculation with empty results."""
        facility = 'Test Facility'
        start_date = datetime(2025, 1, 1)
        end_date = datetime(2025, 1, 2)
        
        summaries = calculate_unmapped_summary_stats(
            [], facility, start_date, end_date
        )
        
        assert len(summaries) == 0


class TestUnmappedDisplayFormatting:
    """Test unmapped hours display formatting."""
    
    @pytest.fixture
    def sample_results_and_summaries(self):
        """Create sample results and summaries for testing."""
        results = [
            UnmappedHoursResult(
                facility='Test Facility',
                category='Unmapped Nursing',
                employee_name='John Doe',
                employee_id='EMP001',
                total_hours=12.0,
                percentage_of_category=60.0,
                analysis_period_start=datetime(2025, 1, 1),
                analysis_period_end=datetime(2025, 1, 2)
            )
        ]
        
        summaries = [
            UnmappedCategorySummary(
                facility='Test Facility',
                category='Unmapped Nursing',
                total_hours=20.0,
                employee_count=2,
                percentage_of_total_unmapped=100.0,
                average_hours_per_employee=10.0,
                analysis_period_start=datetime(2025, 1, 1),
                analysis_period_end=datetime(2025, 1, 2)
            )
        ]
        
        return results, summaries
    
    def test_format_unmapped_hours_for_display_with_data(self, sample_results_and_summaries):
        """Test formatting with data present."""
        results, summaries = sample_results_and_summaries
        
        formatted = format_unmapped_hours_for_display(results, summaries)
        
        assert formatted['has_unmapped_hours'] == True
        assert formatted['total_unmapped_hours'] == 20.0
        assert formatted['total_categories'] == 1
        assert formatted['total_employees'] == 1
        assert len(formatted['categories']) == 1
        assert len(formatted['detailed_results']) == 1
    
    def test_format_unmapped_hours_for_display_empty_data(self):
        """Test formatting with no unmapped data."""
        formatted = format_unmapped_hours_for_display([], [])
        
        assert formatted['has_unmapped_hours'] == False
        assert formatted['total_unmapped_hours'] == 0
        assert formatted['total_categories'] == 0
        assert formatted['total_employees'] == 0
        assert len(formatted['categories']) == 0
        assert len(formatted['detailed_results']) == 0


class TestEndToEndUnmappedAnalysis:
    """Test complete unmapped hours analysis workflow."""
    
    @pytest.fixture
    def complete_facility_data(self):
        """Create complete facility data for end-to-end testing."""
        data = {
            'Facility': ['Test Facility'] * 6,
            'Role': ['Unmapped Nursing', 'Unmapped Nursing', 'RN', 'Unmapped Dietary', 'CNA', 'Other Unmapped'],
            'Date': [datetime(2025, 1, 1)] * 6,
            'ActualHours': [8.0, 6.0, 12.0, 4.0, 8.0, 2.0],
            'EmployeeID': ['EMP001', 'EMP002', 'EMP003', 'EMP004', 'EMP005', 'EMP006'],
            'EmployeeName': ['John Doe', 'Jane Smith', 'Bob Johnson', 'Alice Brown', 'Charlie Wilson', 'Dana White']
        }
        return pd.DataFrame(data)
    
    def test_analyze_unmapped_hours_for_facility_complete_workflow(self, complete_facility_data):
        """Test complete unmapped hours analysis workflow."""
        facility = 'Test Facility'
        start_date = datetime(2025, 1, 1)
        end_date = datetime(2025, 1, 1)
        
        results, summaries = analyze_unmapped_hours_for_facility(
            complete_facility_data, facility, start_date, end_date
        )
        
        # Should have 3 unmapped employees (excluding RN and CNA)
        assert len(results) == 3
        
        # Should have 3 categories (Unmapped Nursing, Unmapped Dietary, Other Unmapped)
        assert len(summaries) == 3
        
        # Check that all unmapped roles are captured
        unmapped_roles = {result.category for result in results}
        expected_roles = {'Unmapped Nursing', 'Unmapped Dietary', 'Other Unmapped'}
        assert unmapped_roles == expected_roles
        
        # Check total hours calculation
        total_unmapped_hours = sum(summary.total_hours for summary in summaries)
        assert total_unmapped_hours == 20.0  # 8.0 + 6.0 + 4.0 + 2.0
    
    def test_analyze_unmapped_hours_for_facility_no_unmapped_data(self):
        """Test analysis with facility data containing no unmapped roles."""
        data = {
            'Facility': ['Test Facility'] * 3,
            'Role': ['RN', 'CNA', 'Nursing Manager'],
            'Date': [datetime(2025, 1, 1)] * 3,
            'ActualHours': [8.0, 8.0, 8.0],
            'EmployeeID': ['EMP001', 'EMP002', 'EMP003'],
            'EmployeeName': ['John Doe', 'Jane Smith', 'Bob Johnson']
        }
        df = pd.DataFrame(data)
        
        facility = 'Test Facility'
        start_date = datetime(2025, 1, 1)
        end_date = datetime(2025, 1, 1)
        
        results, summaries = analyze_unmapped_hours_for_facility(
            df, facility, start_date, end_date
        )
        
        assert len(results) == 0
        assert len(summaries) == 0