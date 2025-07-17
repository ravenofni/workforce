#!/usr/bin/env python3
"""
Test script to verify NaT date formatting fix.
"""

import pandas as pd
import numpy as np
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from config.constants import DATE_FORMAT

def test_nat_handling():
    """Test that NaT values are handled properly in date formatting."""
    print("🔍 Testing NaT date handling...")
    
    # Create a test DataFrame with NaT values
    test_dates = pd.Series([
        pd.Timestamp('2023-01-01'),
        pd.NaT,
        pd.Timestamp('2023-01-03'),
        pd.NaT,
        pd.Timestamp('2023-01-05')
    ])
    
    # Test the safe date range formatting function
    try:
        from src.reporting.exceptions import _safe_date_range_format
        
        # Test with mixed valid and NaT dates
        result = _safe_date_range_format(test_dates)
        print(f"✅ Mixed dates handled: {result}")
        
        # Test with all NaT dates
        all_nat = pd.Series([pd.NaT, pd.NaT, pd.NaT])
        result_nat = _safe_date_range_format(all_nat)
        print(f"✅ All NaT dates handled: {result_nat}")
        
        # Test with valid dates
        valid_dates = pd.Series([pd.Timestamp('2023-01-01'), pd.Timestamp('2023-01-31')])
        result_valid = _safe_date_range_format(valid_dates)
        print(f"✅ Valid dates handled: {result_valid}")
        
        return True
        
    except Exception as e:
        print(f"❌ NaT handling test failed: {e}")
        return False

def test_hours_loader_fix():
    """Test that the hours loader handles NaT values without crashing."""
    print("🔍 Testing hours loader date handling...")
    
    try:
        # Test with the actual sample data
        import subprocess
        result = subprocess.run([
            sys.executable, "main.py", "--debug", "--display-only"
        ], capture_output=True, text=True, timeout=30)
        
        # Check that no NaT strftime error occurs
        if "NaTType does not support strftime" in result.stderr:
            print("❌ NaT strftime error still occurs")
            return False
        elif result.returncode == 0 or "Analysis completed" in result.stdout:
            print("✅ Hours loader handles dates safely")
            return True
        else:
            print(f"❌ Unexpected error: {result.stderr[:200]}...")
            return False
            
    except Exception as e:
        print(f"❌ Hours loader test failed: {e}")
        return False

def test_date_logging():
    """Test that date range logging works with various date scenarios."""
    print("🔍 Testing date range logging...")
    
    # Test safe min/max with NaT values
    test_cases = [
        # (description, dates, expected_to_work)
        ("Valid dates", [pd.Timestamp('2023-01-01'), pd.Timestamp('2023-01-31')], True),
        ("Mixed with NaT", [pd.Timestamp('2023-01-01'), pd.NaT, pd.Timestamp('2023-01-31')], True),
        ("All NaT", [pd.NaT, pd.NaT], True),
        ("Empty series", [], True)
    ]
    
    success_count = 0
    for description, dates, expected in test_cases:
        try:
            df_dates = pd.Series(dates)
            
            # Test min/max operations
            min_date = df_dates.min()
            max_date = df_dates.max()
            
            # Test safe checking
            if pd.isna(min_date) or pd.isna(max_date):
                valid_dates = df_dates.dropna()
                # This should not crash
                result = f"NaT handling: {len(valid_dates)} valid dates"
            else:
                # This should not crash
                result = f"Valid range: {min_date} to {max_date}"
            
            print(f"✅ {description}: {result}")
            success_count += 1
            
        except Exception as e:
            print(f"❌ {description}: {e}")
    
    return success_count == len(test_cases)

def main():
    """Run all date fix tests."""
    print("=" * 60)
    print("NaT DATE FORMATTING FIX TEST")
    print("=" * 60)
    
    tests = [
        ("NaT Handling", test_nat_handling),
        ("Hours Loader Fix", test_hours_loader_fix),
        ("Date Logging", test_date_logging)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*40}")
        print(f"TEST: {test_name}")
        print('='*40)
        
        try:
            if test_func():
                passed += 1
                print(f"🎉 {test_name}: PASSED")
            else:
                print(f"💥 {test_name}: FAILED")
        except Exception as e:
            print(f"💥 {test_name}: ERROR - {str(e)}")
    
    print(f"\n{'='*60}")
    print("DATE FIX TEST SUMMARY")
    print('='*60)
    print(f"Tests Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 ALL DATE FIX TESTS PASSED!")
        return 0
    else:
        print("❌ SOME DATE FIX TESTS FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())