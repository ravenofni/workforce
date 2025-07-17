"""
Role Display Mapping System for Workforce Analytics.

This module provides a comprehensive mapping system that preserves exact model data role names
while offering user-friendly display names for different UI contexts.

The system supports:
- Standard display names: Full, user-friendly names for reports and detailed views
- Short display names: Abbreviated versions for space-constrained UI elements
- Reverse lookups: Finding model roles from display names
- Validation: Ensuring all model roles have proper mappings

Example Usage:
    from src.utils.role_display_mapper import get_standard_display_name, get_short_display_name
    
    # For PDF reports (full readability)
    report_name = get_standard_display_name("Hskpg. Aide")  # "Housekeeping Aide"
    
    # For charts/mobile (space-constrained)
    chart_label = get_short_display_name("Life Enrch. Dir.")  # "Activities"
    
    # Data processing always uses model names
    model_role = "Maint. Suprv."  # Keep exact for calculations
"""

import logging
from typing import Dict, Optional, List, Tuple, Union, Any

from config.constants import RoleDisplayPreference, DEFAULT_ROLE_DISPLAY_PREFERENCES

logger = logging.getLogger(__name__)


# Complete role display mappings for all 44 model data roles
# Key: Exact model role name (must be preserved)
# Value: Dict with 'standard', 'short' display names, 'standard_shift_hours', and 'function'
ROLE_DISPLAY_MAPPINGS: Dict[str, Dict[str, Union[str, float]]] = {
    # Nursing Leadership
    "Director of Nursing": {
        "standard": "Director of Nursing",
        "short": "DON",
        "standard_shift_hours": 8.0,
        "function": "clinical"
    },
    "ADON": {
        "standard": "Assistant Director of Nursing",
        "short": "ADON",
        "standard_shift_hours": 8.0,
        "function": "clinical"
    },
    
    # Nursing Supervisory Roles
    "Nursing Supervisor (RN)": {
        "standard": "Nursing Supervisor (RN)",
        "short": "Nurse Supv",
        "standard_shift_hours": 8.0,
        "function": "clinical"
    },
    "Nursing Supervisor Wknd (RN)": {
        "standard": "Weekend Nursing Supervisor (RN)",
        "short": "Wknd Nurse",
        "standard_shift_hours": 8.0,
        "function": "clinical"
    },
    
    # Assessment and Specialized Nursing
    "RAI (RN)": {
        "standard": "Resident Assessment Coordinator (RN)",
        "short": "RAI-RN",
        "standard_shift_hours": 8.0,
        "function": "clinical"
    },
    "RAI (LPN)": {
        "standard": "Resident Assessment Coordinator (LPN)",
        "short": "RAI-LPN",
        "standard_shift_hours": 8.0,
        "function": "clinical"
    },
    
    # Direct Care Nursing
    "Charge Nurse (LPN)": {
        "standard": "Charge Nurse (LPN)",
        "short": "Charge RN",
        "standard_shift_hours": 8.0,
        "function": "clinical"
    },
    "Wound Care Nurse (LPN)": {
        "standard": "Wound Care Nurse (LPN)",
        "short": "Wound Care",
        "standard_shift_hours": 8.0,
        "function": "clinical"
    },
    "Certified Nursing Assistant": {
        "standard": "Certified Nursing Assistant",
        "short": "CNA",
        "standard_shift_hours": 8.0,
        "function": "clinical"
    },
    "Certified Medication Aide": {
        "standard": "Certified Medication Aide",
        "short": "CMA",
        "standard_shift_hours": 8.0,
        "function": "clinical"
    },
    
    # Therapy Services
    "Physical Therapy": {
        "standard": "Physical Therapy",
        "short": "PT",
        "standard_shift_hours": 8.0,
        "function": "clinical"
    },
    "Occupational Therapy": {
        "standard": "Occupational Therapy",
        "short": "OT",
        "standard_shift_hours": 8.0,
        "function": "clinical"
    },
    "Speech Therapy": {
        "standard": "Speech Therapy",
        "short": "ST",
        "standard_shift_hours": 8.0,
        "function": "clinical"
    },
    "Respiratory Therapy": {
        "standard": "Respiratory Therapy",
        "short": "RT",
        "standard_shift_hours": 8.0,
        "function": "clinical"
    },
    
    # Dietary Services
    "Dining and Nutrition Manager": {
        "standard": "Dining and Nutrition Manager",
        "short": "Dietary Mgr",
        "standard_shift_hours": 8.0,
        "function": "non-clinical"
    },
    "Assistant Dining and Nutrition Manager": {
        "standard": "Assistant Dining and Nutrition Manager",
        "short": "Asst Dietary",
        "standard_shift_hours": 8.0,
        "function": "non-clinical"
    },
    "Cooks": {
        "standard": "Cooks",
        "short": "Cooks",
        "standard_shift_hours": 8.0,
        "function": "non-clinical"
    },
    "Food Svcs. Asst.": {
        "standard": "Food Services Assistant",
        "short": "Food Svc",
        "standard_shift_hours": 8.0,
        "function": "non-clinical"
    },
    
    # Housekeeping and Environmental Services
    "Hskpg. Suprv.": {
        "standard": "Housekeeping Supervisor",
        "short": "Hskpg Supv",
        "standard_shift_hours": 8.0,
        "function": "non-clinical"
    },
    "Hskpg. Aide": {
        "standard": "Housekeeping Aide",
        "short": "Hskpg Aide",
        "standard_shift_hours": 8.0,
        "function": "non-clinical"
    },
    "Floor Tech": {
        "standard": "Floor Technician",
        "short": "Floor Tech",
        "standard_shift_hours": 8.0,
        "function": "non-clinical"
    },
    "Laun. Aid": {
        "standard": "Laundry Aide",
        "short": "Laundry",
        "standard_shift_hours": 8.0,
        "function": "non-clinical"
    },
    
    # Maintenance and Facilities
    "Maint. Suprv.": {
        "standard": "Maintenance Supervisor",
        "short": "Maint Supv",
        "standard_shift_hours": 8.0,
        "function": "non-clinical"
    },
    "Maint. Asst.": {
        "standard": "Maintenance Assistant",
        "short": "Maint Asst",
        "standard_shift_hours": 8.0,
        "function": "non-clinical"
    },
    "Weekend Maint. Asst.": {
        "standard": "Weekend Maintenance Assistant",
        "short": "Wknd Maint",
        "standard_shift_hours": 8.0,
        "function": "non-clinical"
    },
    
    # Social Services
    "Soc. Work. (Degreed)": {
        "standard": "Social Worker",
        "short": "Social Work",
        "standard_shift_hours": 8.0,
        "function": "clinical"
    },
    "Soc. Svcs. Coord": {
        "standard": "Social Services Coordinator",
        "short": "Soc Svcs",
        "standard_shift_hours": 8.0,
        "function": "clinical"
    },
    
    # Life Enrichment/Activities
    "Life Enrch. Dir.": {
        "standard": "Life Enrichment Director",
        "short": "Activities Dir",
        "standard_shift_hours": 8.0,
        "function": "non-clinical"
    },
    "Life Enrch. Asst.": {
        "standard": "Life Enrichment Assistant",
        "short": "Activities Asst",
        "standard_shift_hours": 8.0,
        "function": "non-clinical"
    },
    
    # Administration and Management
    "SNF Admin": {
        "standard": "SNF Administrator",
        "short": "Admin",
        "standard_shift_hours": 8.0,
        "function": "non-clinical"
    },
    "SNF Asst. Admin": {
        "standard": "SNF Assistant Administrator",
        "short": "Asst Admin",
        "standard_shift_hours": 8.0,
        "function": "non-clinical"
    },
    "Business Lead": {
        "standard": "Business Lead",
        "short": "Bus Lead",
        "standard_shift_hours": 8.0,
        "function": "non-clinical"
    },
    
    # Coordination and Support
    "Sched Coord": {
        "standard": "Scheduling Coordinator",
        "short": "Scheduling",
        "standard_shift_hours": 8.0,
        "function": "non-clinical"
    },
    "HR Coord": {
        "standard": "HR Coordinator",
        "short": "HR",
        "standard_shift_hours": 8.0,
        "function": "non-clinical"
    },
    "HC Navigator (5 days)": {
        "standard": "Healthcare Navigator (5 days)",
        "short": "Navigator",
        "standard_shift_hours": 8.0,
        "function": "non-clinical"
    },
    
    # Health Information Management
    "HIM Tech (5 days)": {
        "standard": "Health Information Management Technician",
        "short": "HIM Tech",
        "standard_shift_hours": 8.0,
        "function": "non-clinical"
    },
    
    # Clinical Support
    "Other Clinical": {
        "standard": "Other Clinical Staff",
        "short": "Other Clin",
        "standard_shift_hours": 8.0,
        "function": "clinical"
    },
    
    # Unmapped Categories
    "Unmapped Nursing": {
        "standard": "Unmapped Nursing",
        "short": "Unmap Nurs",
        "standard_shift_hours": 0.0,
        "function": "clinical"
    },
    "Unmapped Dietary": {
        "standard": "Unmapped Dietary",
        "short": "Unmap Diet",
        "standard_shift_hours": 0.0,
        "function": "non-clinical"
    },
    "Unmapped Hskp": {
        "standard": "Unmapped Housekeeping",
        "short": "Unmap HK",
        "standard_shift_hours": 0.0,
        "function": "non-clinical"
    },
    "Unmapped Life Enrichment": {
        "standard": "Unmapped Life Enrichment",
        "short": "Unmap Act",
        "standard_shift_hours": 0.0,
        "function": "non-clinical"
    },
    "Unmapped Maintenance": {
        "standard": "Unmapped Maintenance",
        "short": "Unmap Maint",
        "standard_shift_hours": 0.0,
        "function": "non-clinical"
    },
    "Unmapped Admin": {
        "standard": "Unmapped Administration",
        "short": "Unmap Admin",
        "standard_shift_hours": 0.0,
        "function": "non-clinical"
    },
    "Other Unmapped": {
        "standard": "Other Unmapped",
        "short": "Other",
        "standard_shift_hours": 0.0,
        "function": "non-clinical"
    },
    
    # Catch-all for unrecognized roles
    "Unknown": {
        "standard": "Unknown Role",
        "short": "Unknown",
        "standard_shift_hours": 0.0,
        "function": "non-clinical"
    }
}


def get_standard_display_name(model_role: str) -> str:
    """
    Get the standard (full) display name for a model role.
    
    Args:
        model_role: Exact model role name from data
        
    Returns:
        User-friendly standard display name
        
    Raises:
        KeyError: If model role is not found in mappings
    """
    if model_role not in ROLE_DISPLAY_MAPPINGS:
        logger.warning(f"Model role '{model_role}' not found in display mappings")
        raise KeyError(f"No display mapping found for model role: '{model_role}'")
    
    return ROLE_DISPLAY_MAPPINGS[model_role]["standard"]


def get_short_display_name(model_role: str) -> str:
    """
    Get the short (abbreviated) display name for a model role.
    
    Args:
        model_role: Exact model role name from data
        
    Returns:
        Abbreviated display name for space-constrained contexts
        
    Raises:
        KeyError: If model role is not found in mappings
    """
    if model_role not in ROLE_DISPLAY_MAPPINGS:
        logger.warning(f"Model role '{model_role}' not found in display mappings")
        raise KeyError(f"No display mapping found for model role: '{model_role}'")
    
    return ROLE_DISPLAY_MAPPINGS[model_role]["short"]


def get_standard_shift_hours(model_role: str) -> float:
    """
    Get the standard shift hours for a model role.
    
    Args:
        model_role: Exact model role name from data
        
    Returns:
        Standard shift hours for the role
        
    Raises:
        KeyError: If model role is not found in mappings
    """
    if model_role not in ROLE_DISPLAY_MAPPINGS:
        logger.warning(f"Model role '{model_role}' not found in display mappings")
        raise KeyError(f"No display mapping found for model role: '{model_role}'")
    
    return float(ROLE_DISPLAY_MAPPINGS[model_role]["standard_shift_hours"])


def get_role_function(model_role: str) -> str:
    """
    Get the function classification (clinical/non-clinical) for a model role.
    
    Args:
        model_role: Exact model role name from data
        
    Returns:
        Role function: "clinical" or "non-clinical"
        
    Raises:
        KeyError: If model role is not found in mappings
    """
    if model_role not in ROLE_DISPLAY_MAPPINGS:
        logger.warning(f"Model role '{model_role}' not found in display mappings")
        raise KeyError(f"No display mapping found for model role: '{model_role}'")
    
    return ROLE_DISPLAY_MAPPINGS[model_role]["function"]


def get_roles_by_function(function: str) -> List[str]:
    """
    Get all roles that match a specific function classification.
    
    Args:
        function: Function to filter by ("clinical" or "non-clinical")
        
    Returns:
        List of role names that match the function
        
    Raises:
        ValueError: If function is not "clinical" or "non-clinical"
    """
    if function not in ["clinical", "non-clinical"]:
        raise ValueError(f"Function must be 'clinical' or 'non-clinical', got: {function}")
    
    return [role for role, mapping in ROLE_DISPLAY_MAPPINGS.items() 
            if mapping["function"] == function]


def get_clinical_roles() -> List[str]:
    """
    Get all clinical roles.
    
    Returns:
        List of clinical role names
    """
    return get_roles_by_function("clinical")


def get_non_clinical_roles() -> List[str]:
    """
    Get all non-clinical roles.
    
    Returns:
        List of non-clinical role names
    """
    return get_roles_by_function("non-clinical")


def get_all_roles_with_shift_hours() -> Dict[str, float]:
    """
    Get all roles with their standard shift hours.
    
    Returns:
        Dictionary mapping role names to their standard shift hours
    """
    return {role: float(mapping["standard_shift_hours"]) 
            for role, mapping in ROLE_DISPLAY_MAPPINGS.items()}


def get_all_roles_with_functions() -> Dict[str, str]:
    """
    Get all roles with their function classifications.
    
    Returns:
        Dictionary mapping role names to their function ("clinical" or "non-clinical")
    """
    return {role: mapping["function"] 
            for role, mapping in ROLE_DISPLAY_MAPPINGS.items()}


def get_role_functions_for_roles(role_list: List[str]) -> Dict[str, str]:
    """
    Get function classifications for a list of roles.
    
    Args:
        role_list: List of role names to get functions for
        
    Returns:
        Dictionary mapping role names to their functions
        Roles not found in mappings will be excluded from results
    """
    result = {}
    for role in role_list:
        if role in ROLE_DISPLAY_MAPPINGS:
            result[role] = ROLE_DISPLAY_MAPPINGS[role]["function"]
        else:
            logger.warning(f"Role '{role}' not found in display mappings")
    
    return result


def update_role_shift_hours(model_role: str, hours: float) -> bool:
    """
    Update standard shift hours for a role.
    
    Args:
        model_role: Exact model role name
        hours: New standard shift hours (must be positive)
        
    Returns:
        True if successful, False if role not found
        
    Raises:
        ValueError: If hours is negative or zero
    """
    if hours <= 0:
        raise ValueError("Standard shift hours must be positive")
    
    if model_role not in ROLE_DISPLAY_MAPPINGS:
        logger.warning(f"Cannot update shift hours - role '{model_role}' not found")
        return False
    
    ROLE_DISPLAY_MAPPINGS[model_role]["standard_shift_hours"] = float(hours)
    logger.info(f"Updated standard shift hours for '{model_role}' to {hours}")
    return True


def get_model_role_from_standard_display(display_name: str) -> Optional[str]:
    """
    Reverse lookup: Find model role from standard display name.
    
    Args:
        display_name: Standard display name to look up
        
    Returns:
        Model role name if found, None otherwise
    """
    for model_role, mappings in ROLE_DISPLAY_MAPPINGS.items():
        if mappings["standard"] == display_name:
            return model_role
    
    logger.warning(f"Standard display name '{display_name}' not found in mappings")
    return None


def get_model_role_from_short_display(display_name: str) -> Optional[str]:
    """
    Reverse lookup: Find model role from short display name.
    
    Args:
        display_name: Short display name to look up
        
    Returns:
        Model role name if found, None otherwise
    """
    for model_role, mappings in ROLE_DISPLAY_MAPPINGS.items():
        if mappings["short"] == display_name:
            return model_role
    
    logger.warning(f"Short display name '{display_name}' not found in mappings")
    return None


def get_model_role_from_any_display(display_name: str) -> Optional[str]:
    """
    Reverse lookup: Find model role from either standard or short display name.
    
    Args:
        display_name: Display name (standard or short) to look up
        
    Returns:
        Model role name if found, None otherwise
    """
    # Try standard display name first
    model_role = get_model_role_from_standard_display(display_name)
    if model_role:
        return model_role
    
    # Try short display name
    return get_model_role_from_short_display(display_name)


def get_all_display_mappings() -> Dict[str, Dict[str, str]]:
    """
    Get all role display mappings.
    
    Returns:
        Complete mapping dictionary
    """
    return ROLE_DISPLAY_MAPPINGS.copy()


def get_all_model_roles() -> List[str]:
    """
    Get list of all model role names.
    
    Returns:
        Sorted list of all model role names
    """
    return sorted(ROLE_DISPLAY_MAPPINGS.keys())


def get_all_standard_display_names() -> List[str]:
    """
    Get list of all standard display names.
    
    Returns:
        Sorted list of all standard display names
    """
    return sorted([mapping["standard"] for mapping in ROLE_DISPLAY_MAPPINGS.values()])


def get_all_short_display_names() -> List[str]:
    """
    Get list of all short display names.
    
    Returns:
        Sorted list of all short display names
    """
    return sorted([mapping["short"] for mapping in ROLE_DISPLAY_MAPPINGS.values()])


def validate_model_roles_coverage(model_roles: List[str]) -> Tuple[bool, List[str]]:
    """
    Validate that all provided model roles have display mappings.
    
    Args:
        model_roles: List of model role names to validate
        
    Returns:
        Tuple of (all_covered: bool, missing_roles: List[str])
    """
    missing_roles = []
    for role in model_roles:
        if role not in ROLE_DISPLAY_MAPPINGS:
            missing_roles.append(role)
    
    all_covered = len(missing_roles) == 0
    
    if not all_covered:
        logger.error(f"Missing display mappings for {len(missing_roles)} roles: {missing_roles}")
    else:
        logger.info(f"All {len(model_roles)} model roles have display mappings")
    
    return all_covered, missing_roles


def validate_unique_display_names() -> Tuple[bool, List[str], List[str]]:
    """
    Validate that all display names are unique within their type.
    
    Returns:
        Tuple of (all_unique: bool, duplicate_standard: List[str], duplicate_short: List[str])
    """
    standard_names = [mapping["standard"] for mapping in ROLE_DISPLAY_MAPPINGS.values()]
    short_names = [mapping["short"] for mapping in ROLE_DISPLAY_MAPPINGS.values()]
    
    # Find duplicates
    duplicate_standard = [name for name in set(standard_names) if standard_names.count(name) > 1]
    duplicate_short = [name for name in set(short_names) if short_names.count(name) > 1]
    
    all_unique = len(duplicate_standard) == 0 and len(duplicate_short) == 0
    
    if not all_unique:
        logger.error(f"Duplicate display names found - Standard: {duplicate_standard}, Short: {duplicate_short}")
    else:
        logger.info("All display names are unique within their types")
    
    return all_unique, duplicate_standard, duplicate_short


def get_role_mapping_summary() -> Dict[str, int]:
    """
    Get summary statistics about the role mappings.
    
    Returns:
        Dictionary with mapping statistics
    """
    total_roles = len(ROLE_DISPLAY_MAPPINGS)
    unique_standard = len(set(mapping["standard"] for mapping in ROLE_DISPLAY_MAPPINGS.values()))
    unique_short = len(set(mapping["short"] for mapping in ROLE_DISPLAY_MAPPINGS.values()))
    
    return {
        "total_model_roles": total_roles,
        "unique_standard_names": unique_standard,
        "unique_short_names": unique_short,
        "standard_uniqueness": unique_standard == total_roles,
        "short_uniqueness": unique_short == total_roles
    }


# Convenience functions for common use cases
def format_role_for_report(model_role: str, use_short: bool = False) -> str:
    """
    Format a role name for report display.
    
    Args:
        model_role: Model role name
        use_short: If True, use short display name; otherwise use standard
        
    Returns:
        Formatted role name for display
    """
    try:
        if use_short:
            return get_short_display_name(model_role)
        else:
            return get_standard_display_name(model_role)
    except KeyError:
        logger.warning(f"Using original role name for unmapped role: '{model_role}'")
        return model_role


def format_roles_for_chart(model_roles: List[str], max_length: Optional[int] = None) -> List[str]:
    """
    Format a list of role names for chart display, automatically choosing short names if needed.
    
    Args:
        model_roles: List of model role names
        max_length: Maximum character length for display names (auto-chooses short if exceeded)
        
    Returns:
        List of formatted role names optimized for chart display
    """
    formatted_roles = []
    
    for role in model_roles:
        try:
            standard_name = get_standard_display_name(role)
            short_name = get_short_display_name(role)
            
            # Choose short name if max_length is specified and standard name is too long
            if max_length and len(standard_name) > max_length:
                formatted_roles.append(short_name)
            else:
                formatted_roles.append(standard_name)
                
        except KeyError:
            logger.warning(f"Using original role name for unmapped role: '{role}'")
            formatted_roles.append(role)
    
    return formatted_roles


def get_role_display_name_by_context(model_role: str, context: str) -> str:
    """
    Get the appropriate display name for a role based on context.
    
    Args:
        model_role: Exact model role name from data
        context: Display context (e.g., "reports", "charts", "tables", "mobile", "api", "export")
        
    Returns:
        Appropriate display name based on context preferences
        
    Raises:
        KeyError: If model role is not found in mappings
        ValueError: If context is not recognized
    """
    if context not in DEFAULT_ROLE_DISPLAY_PREFERENCES:
        logger.warning(f"Unknown context '{context}', using standard display preference")
        preference = RoleDisplayPreference.STANDARD
    else:
        preference = DEFAULT_ROLE_DISPLAY_PREFERENCES[context]
    
    return get_role_display_name_by_preference(model_role, preference)


def get_role_display_name_by_preference(model_role: str, preference: RoleDisplayPreference) -> str:
    """
    Get the display name for a role based on display preference.
    
    Args:
        model_role: Exact model role name from data
        preference: Display preference (STANDARD, SHORT, or MODEL)
        
    Returns:
        Display name based on preference
        
    Raises:
        KeyError: If model role is not found in mappings
        ValueError: If preference is not recognized
    """
    if preference == RoleDisplayPreference.STANDARD:
        return get_standard_display_name(model_role)
    elif preference == RoleDisplayPreference.SHORT:
        return get_short_display_name(model_role)
    elif preference == RoleDisplayPreference.MODEL:
        return model_role  # Return original model role name
    else:
        raise ValueError(f"Unknown display preference: {preference}")


def format_roles_by_context(model_roles: List[str], context: str) -> List[str]:
    """
    Format a list of role names based on context preferences.
    
    Args:
        model_roles: List of model role names
        context: Display context for determining appropriate names
        
    Returns:
        List of formatted role names based on context
    """
    return [get_role_display_name_by_context(role, context) for role in model_roles]


def get_context_preferences() -> Dict[str, str]:
    """
    Get the current context-based display preferences.
    
    Returns:
        Dictionary mapping contexts to their display preferences
    """
    return {context: pref.value for context, pref in DEFAULT_ROLE_DISPLAY_PREFERENCES.items()}


# Initialize logging for this module
logger.info(f"Role display mapper initialized with {len(ROLE_DISPLAY_MAPPINGS)} role mappings")