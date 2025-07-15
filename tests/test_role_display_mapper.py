"""
Comprehensive test suite for role display mapping system.

Tests the role display mapper that provides user-friendly display names
while preserving exact model data role names.
"""

import pytest
import pandas as pd
from typing import List

from src.utils.role_display_mapper import (
    get_standard_display_name,
    get_short_display_name,
    get_model_role_from_standard_display,
    get_model_role_from_short_display,
    get_model_role_from_any_display,
    get_all_display_mappings,
    get_all_model_roles,
    get_all_standard_display_names,
    get_all_short_display_names,
    validate_model_roles_coverage,
    validate_unique_display_names,
    get_role_mapping_summary,
    format_role_for_report,
    format_roles_for_chart,
    ROLE_DISPLAY_MAPPINGS
)


class TestRoleDisplayMappings:
    """Test the core display mapping functionality."""
    
    def test_all_44_model_roles_have_mappings(self):
        """
        Test that all 44 model data roles have display mappings.
        
        Verifies that every role from the model data has both
        standard and short display name mappings.
        """
        # Load actual model data to get the complete role list
        df = pd.read_csv('examples/SampleModelData.csv')
        actual_model_roles = sorted(df['STAFF_ROLE_NAME'].unique())
        
        # Verify we have exactly 44 roles as expected
        assert len(actual_model_roles) == 44, f"Expected 44 model roles, found {len(actual_model_roles)}"
        
        # Verify all model roles have mappings
        mapped_roles = sorted(ROLE_DISPLAY_MAPPINGS.keys())
        assert mapped_roles == actual_model_roles, f"Mapped roles don't match model data roles"
        
        # Verify each mapping has both standard and short names
        for role in actual_model_roles:
            mapping = ROLE_DISPLAY_MAPPINGS[role]
            assert "standard" in mapping, f"Role '{role}' missing standard display name"
            assert "short" in mapping, f"Role '{role}' missing short display name"
            assert mapping["standard"], f"Role '{role}' has empty standard display name"
            assert mapping["short"], f"Role '{role}' has empty short display name"
    
    def test_get_standard_display_name(self):
        """
        Test retrieval of standard display names.
        
        Verifies that standard display names are returned correctly
        for valid model roles.
        """
        test_cases = [
            ("Director of Nursing", "Director of Nursing"),
            ("ADON", "Assistant Director of Nursing"),
            ("Hskpg. Aide", "Housekeeping Aide"),
            ("Maint. Suprv.", "Maintenance Supervisor"),
            ("Food Svcs. Asst.", "Food Services Assistant"),
            ("Life Enrch. Dir.", "Life Enrichment Director"),
            ("Soc. Work. (Degreed)", "Social Worker (Degreed)"),
            ("SNF Admin", "SNF Administrator"),
        ]
        
        for model_role, expected_standard in test_cases:
            result = get_standard_display_name(model_role)
            assert result == expected_standard, f"'{model_role}' should have standard name '{expected_standard}', got '{result}'"
    
    def test_get_short_display_name(self):
        """
        Test retrieval of short display names.
        
        Verifies that short display names are returned correctly
        for valid model roles.
        """
        test_cases = [
            ("Director of Nursing", "DON"),
            ("Certified Nursing Assistant", "CNA"),
            ("Physical Therapy", "PT"),
            ("Hskpg. Aide", "Housekeeping"),
            ("Life Enrch. Dir.", "Activities"),
            ("Food Svcs. Asst.", "Food Svc"),
            ("Weekend Maint. Asst.", "Wknd Maint"),
            ("HC Navigator (5 days)", "Navigator"),
        ]
        
        for model_role, expected_short in test_cases:
            result = get_short_display_name(model_role)
            assert result == expected_short, f"'{model_role}' should have short name '{expected_short}', got '{result}'"
    
    def test_invalid_model_role_handling(self):
        """
        Test handling of invalid/unmapped model roles.
        
        Verifies that appropriate errors are raised for roles
        not found in the mapping system.
        """
        invalid_roles = [
            "Nonexistent Role",
            "Invalid Role Name",
            "",
            "Random Text"
        ]
        
        for invalid_role in invalid_roles:
            with pytest.raises(KeyError):
                get_standard_display_name(invalid_role)
            
            with pytest.raises(KeyError):
                get_short_display_name(invalid_role)
    
    def test_reverse_lookup_standard_display(self):
        """
        Test reverse lookup from standard display names to model roles.
        
        Verifies that we can find model roles from their standard
        display names.
        """
        test_cases = [
            ("Housekeeping Aide", "Hskpg. Aide"),
            ("Maintenance Supervisor", "Maint. Suprv."),
            ("Food Services Assistant", "Food Svcs. Asst."),
            ("Life Enrichment Director", "Life Enrch. Dir."),
            ("Assistant Director of Nursing", "ADON"),
        ]
        
        for standard_display, expected_model in test_cases:
            result = get_model_role_from_standard_display(standard_display)
            assert result == expected_model, f"Standard display '{standard_display}' should map to '{expected_model}', got '{result}'"
    
    def test_reverse_lookup_short_display(self):
        """
        Test reverse lookup from short display names to model roles.
        
        Verifies that we can find model roles from their short
        display names.
        """
        test_cases = [
            ("DON", "Director of Nursing"),
            ("CNA", "Certified Nursing Assistant"),
            ("PT", "Physical Therapy"),
            ("Activities", "Life Enrch. Dir."),
            ("Housekeeping", "Hskpg. Aide"),
        ]
        
        for short_display, expected_model in test_cases:
            result = get_model_role_from_short_display(short_display)
            assert result == expected_model, f"Short display '{short_display}' should map to '{expected_model}', got '{result}'"
    
    def test_reverse_lookup_any_display(self):
        """
        Test reverse lookup from any display name (standard or short).
        
        Verifies that the any_display function works for both
        standard and short display names.
        """
        # Test with standard names
        standard_result = get_model_role_from_any_display("Housekeeping Aide")
        assert standard_result == "Hskpg. Aide"
        
        # Test with short names
        short_result = get_model_role_from_any_display("DON")
        assert short_result == "Director of Nursing"
        
        # Test with invalid name
        invalid_result = get_model_role_from_any_display("Invalid Role")
        assert invalid_result is None
    
    def test_get_all_functions(self):
        """
        Test functions that return complete lists of roles/names.
        
        Verifies that the getter functions return the expected
        number of items and correct data types.
        """
        # Test all model roles
        all_model_roles = get_all_model_roles()
        assert len(all_model_roles) == 44
        assert all(isinstance(role, str) for role in all_model_roles)
        assert all_model_roles == sorted(all_model_roles)  # Should be sorted
        
        # Test all standard display names
        all_standard = get_all_standard_display_names()
        assert len(all_standard) == 44
        assert all(isinstance(name, str) for name in all_standard)
        assert all_standard == sorted(all_standard)  # Should be sorted
        
        # Test all short display names
        all_short = get_all_short_display_names()
        assert len(all_short) == 44
        assert all(isinstance(name, str) for name in all_short)
        assert all_short == sorted(all_short)  # Should be sorted
        
        # Test all mappings
        all_mappings = get_all_display_mappings()
        assert len(all_mappings) == 44
        assert isinstance(all_mappings, dict)


class TestValidationFunctions:
    """Test validation and utility functions."""
    
    def test_validate_model_roles_coverage_complete(self):
        """
        Test validation with complete model role coverage.
        
        Verifies that validation passes when all model roles
        have display mappings.
        """
        # Load actual model data
        df = pd.read_csv('examples/SampleModelData.csv')
        model_roles = df['STAFF_ROLE_NAME'].unique().tolist()
        
        # Should pass validation
        all_covered, missing_roles = validate_model_roles_coverage(model_roles)
        assert all_covered is True
        assert missing_roles == []
    
    def test_validate_model_roles_coverage_incomplete(self):
        """
        Test validation with incomplete model role coverage.
        
        Verifies that validation fails appropriately when some
        model roles are missing display mappings.
        """
        # Include some valid and some invalid roles
        test_roles = [
            "Director of Nursing",  # Valid
            "Invalid Role 1",       # Invalid
            "Hskpg. Aide",         # Valid
            "Invalid Role 2",       # Invalid
        ]
        
        all_covered, missing_roles = validate_model_roles_coverage(test_roles)
        assert all_covered is False
        assert len(missing_roles) == 2
        assert "Invalid Role 1" in missing_roles
        assert "Invalid Role 2" in missing_roles
    
    def test_validate_unique_display_names(self):
        """
        Test validation of display name uniqueness.
        
        Verifies that all display names are unique within their type
        (no duplicate standard names, no duplicate short names).
        """
        all_unique, duplicate_standard, duplicate_short = validate_unique_display_names()
        
        # All display names should be unique
        assert all_unique is True
        assert duplicate_standard == []
        assert duplicate_short == []
    
    def test_get_role_mapping_summary(self):
        """
        Test the role mapping summary function.
        
        Verifies that summary statistics are calculated correctly.
        """
        summary = get_role_mapping_summary()
        
        # Check expected keys
        expected_keys = [
            "total_model_roles",
            "unique_standard_names", 
            "unique_short_names",
            "standard_uniqueness",
            "short_uniqueness"
        ]
        for key in expected_keys:
            assert key in summary
        
        # Check values
        assert summary["total_model_roles"] == 44
        assert summary["unique_standard_names"] == 44  # Should all be unique
        assert summary["unique_short_names"] == 44     # Should all be unique
        assert summary["standard_uniqueness"] is True
        assert summary["short_uniqueness"] is True


class TestConvenienceFunctions:
    """Test convenience functions for common use cases."""
    
    def test_format_role_for_report_standard(self):
        """
        Test formatting roles for reports using standard names.
        
        Verifies that standard display names are used by default
        for report formatting.
        """
        test_cases = [
            ("Hskpg. Aide", "Housekeeping Aide"),
            ("Life Enrch. Dir.", "Life Enrichment Director"),
            ("SNF Admin", "SNF Administrator"),
        ]
        
        for model_role, expected_display in test_cases:
            result = format_role_for_report(model_role, use_short=False)
            assert result == expected_display
    
    def test_format_role_for_report_short(self):
        """
        Test formatting roles for reports using short names.
        
        Verifies that short display names are used when requested
        for report formatting.
        """
        test_cases = [
            ("Director of Nursing", "DON"),
            ("Physical Therapy", "PT"),
            ("Life Enrch. Dir.", "Activities"),
        ]
        
        for model_role, expected_display in test_cases:
            result = format_role_for_report(model_role, use_short=True)
            assert result == expected_display
    
    def test_format_role_for_report_invalid(self):
        """
        Test formatting invalid roles for reports.
        
        Verifies that original role names are returned when
        no mapping is found.
        """
        invalid_role = "Invalid Role Name"
        result = format_role_for_report(invalid_role)
        assert result == invalid_role  # Should return original
    
    def test_format_roles_for_chart_no_length_limit(self):
        """
        Test formatting roles for charts without length limits.
        
        Verifies that standard names are used when no length
        constraint is specified.
        """
        model_roles = ["Director of Nursing", "Hskpg. Aide", "Physical Therapy"]
        expected = ["Director of Nursing", "Housekeeping Aide", "Physical Therapy"]
        
        result = format_roles_for_chart(model_roles)
        assert result == expected
    
    def test_format_roles_for_chart_with_length_limit(self):
        """
        Test formatting roles for charts with length limits.
        
        Verifies that short names are automatically chosen when
        standard names exceed the length limit.
        """
        model_roles = ["Director of Nursing", "Hskpg. Aide", "Physical Therapy"]
        # Length limit of 10 should force short names for longer roles
        expected = ["DON", "Housekeeping", "PT"]  # "Housekeeping" is still > 10, but it's the short version
        
        result = format_roles_for_chart(model_roles, max_length=10)
        # Director of Nursing (18 chars) -> DON (3 chars)
        # Physical Therapy (16 chars) -> PT (2 chars)
        # Hskpg. Aide -> Housekeeping Aide (16 chars) -> Housekeeping (11 chars)
        
        # Should use short names for roles that exceed limit
        assert "DON" in result
        assert "PT" in result
    
    def test_format_roles_for_chart_invalid_roles(self):
        """
        Test formatting invalid roles for charts.
        
        Verifies that original role names are preserved when
        no mapping is found.
        """
        model_roles = ["Director of Nursing", "Invalid Role", "Physical Therapy"]
        result = format_roles_for_chart(model_roles)
        
        # Valid roles should be mapped, invalid should be preserved
        assert "Director of Nursing" in result
        assert "Invalid Role" in result  # Should be unchanged
        assert "Physical Therapy" in result


class TestModelDataIntegration:
    """Test integration with actual model data."""
    
    @pytest.fixture
    def model_data_roles(self):
        """Load actual model data roles for testing."""
        df = pd.read_csv('examples/SampleModelData.csv')
        return sorted(df['STAFF_ROLE_NAME'].unique())
    
    def test_complete_model_data_coverage(self, model_data_roles):
        """
        Test that all model data roles have display mappings.
        
        Verifies complete coverage of all roles found in the
        actual model data file.
        """
        # Every model role should have a mapping
        for role in model_data_roles:
            # Should not raise KeyError
            standard_name = get_standard_display_name(role)
            short_name = get_short_display_name(role)
            
            # Names should not be empty
            assert standard_name, f"Empty standard name for role: {role}"
            assert short_name, f"Empty short name for role: {role}"
    
    def test_model_data_role_preservation(self, model_data_roles):
        """
        Test that model data role names are preserved exactly.
        
        Verifies that the mapping keys exactly match the model
        data role names without modification.
        """
        mapped_roles = sorted(ROLE_DISPLAY_MAPPINGS.keys())
        assert mapped_roles == model_data_roles, "Mapped roles must exactly match model data roles"
    
    def test_bidirectional_mapping_consistency(self, model_data_roles):
        """
        Test that bidirectional mappings are consistent.
        
        Verifies that model_role -> display_name -> model_role
        round trips work correctly.
        """
        for role in model_data_roles:
            # Test standard display round trip
            standard_display = get_standard_display_name(role)
            reverse_role = get_model_role_from_standard_display(standard_display)
            assert reverse_role == role, f"Standard round trip failed for {role}"
            
            # Test short display round trip
            short_display = get_short_display_name(role)
            reverse_role = get_model_role_from_short_display(short_display)
            assert reverse_role == role, f"Short round trip failed for {role}"


class TestDisplayNameQuality:
    """Test the quality and consistency of display names."""
    
    def test_standard_names_are_readable(self):
        """
        Test that standard display names are more readable than model names.
        
        Verifies that abbreviated model names are expanded to
        full, user-friendly forms.
        """
        readability_improvements = [
            ("Hskpg. Aide", "Housekeeping Aide"),
            ("Maint. Suprv.", "Maintenance Supervisor"),
            ("Food Svcs. Asst.", "Food Services Assistant"),
            ("Life Enrch. Dir.", "Life Enrichment Director"),
            ("Soc. Work. (Degreed)", "Social Worker (Degreed)"),
        ]
        
        for model_role, expected_readable in readability_improvements:
            standard_name = get_standard_display_name(model_role)
            assert standard_name == expected_readable
            # Standard name should be longer/more descriptive than model name
            assert len(standard_name) >= len(model_role)
    
    def test_short_names_are_concise(self):
        """
        Test that short display names are appropriately concise.
        
        Verifies that short names are significantly shorter
        than standard names for space-constrained contexts.
        """
        for model_role, mappings in ROLE_DISPLAY_MAPPINGS.items():
            standard_name = mappings["standard"]
            short_name = mappings["short"]
            
            # Short names should generally be shorter than standard names
            # (allowing some exceptions for already short roles)
            if len(standard_name) > 10:
                assert len(short_name) < len(standard_name), f"Short name '{short_name}' should be shorter than standard name '{standard_name}'"
            
            # Short names should be reasonable length for UI elements
            assert len(short_name) <= 15, f"Short name '{short_name}' is too long for space-constrained contexts"
    
    def test_no_empty_display_names(self):
        """
        Test that no display names are empty or whitespace-only.
        
        Verifies data quality of all display mappings.
        """
        for model_role, mappings in ROLE_DISPLAY_MAPPINGS.items():
            standard_name = mappings["standard"].strip()
            short_name = mappings["short"].strip()
            
            assert standard_name, f"Empty standard name for role: {model_role}"
            assert short_name, f"Empty short name for role: {model_role}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])