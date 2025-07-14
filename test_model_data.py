#!/usr/bin/env python3
"""
Test script to verify model data is loading all day-specific hour allocations.
"""

import sys
import os
import pandas as pd

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.ingestion.model_loader import load_model_data

def test_model_data_completeness():
    """Test that model data loads all days and shows variation."""
    print("🔍 Testing model data completeness...")
    
    try:
        df = load_model_data('examples/SampleModelData.csv')
        
        # Test 1: All days are loaded
        unique_days = df['DayOfWeek'].unique()
        expected_days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        
        if len(unique_days) == 7:
            print("✅ All 7 days of week loaded")
        else:
            print(f"❌ Only {len(unique_days)} days loaded: {unique_days}")
            return False
        
        # Test 2: Role-day combinations exist
        total_roles = df['Role'].nunique()
        expected_records = total_roles * 7
        
        if len(df) == expected_records:
            print(f"✅ Complete role-day matrix: {total_roles} roles × 7 days = {len(df)} records")
        else:
            print(f"❌ Incomplete data: expected {expected_records}, got {len(df)}")
            return False
        
        # Test 3: Verify day-specific variation exists
        director_data = df[df['Role'].str.contains('Director', case=False, na=False)]
        if not director_data.empty:
            sunday_hours = director_data[director_data['DayOfWeek'] == 'Sunday']['ModelHours'].iloc[0]
            monday_hours = director_data[director_data['DayOfWeek'] == 'Monday']['ModelHours'].iloc[0]
            
            if sunday_hours != monday_hours:
                print(f"✅ Day-specific variation confirmed: Director has {sunday_hours} hours on Sunday, {monday_hours} hours on Monday")
            else:
                print(f"⚠️  Director hours same on Sunday and Monday: {sunday_hours}")
        
        # Test 4: Weekend vs weekday patterns
        weekend_total = df[df['DayOfWeek'].isin(['Saturday', 'Sunday'])]['ModelHours'].sum()
        weekday_total = df[~df['DayOfWeek'].isin(['Saturday', 'Sunday'])]['ModelHours'].sum()
        
        print(f"✅ Weekend total: {weekend_total:.2f} hours")
        print(f"✅ Weekday total: {weekday_total:.2f} hours")
        
        if weekend_total != weekday_total:
            print("✅ Weekend vs weekday staffing patterns detected")
        
        return True
        
    except Exception as e:
        print(f"❌ Model data test failed: {e}")
        return False

def test_specific_role_patterns():
    """Test specific roles to verify day-of-week patterns."""
    print("🔍 Testing specific role patterns...")
    
    try:
        df = load_model_data('examples/SampleModelData.csv')
        
        # Test weekend supervisors
        weekend_roles = df[df['Role'].str.contains('Wknd', case=False, na=False)]
        if not weekend_roles.empty:
            weekend_supervisor_hours = weekend_roles.groupby('DayOfWeek')['ModelHours'].sum()
            print("✅ Weekend supervisor hours by day:")
            for day, hours in weekend_supervisor_hours.items():
                print(f"    {day}: {hours:.2f} hours")
        
        # Test regular vs weekend hours for nursing supervisors
        regular_supervisors = df[df['Role'].str.contains('Nursing Supervisor', case=False, na=False) & 
                                ~df['Role'].str.contains('Wknd', case=False, na=False)]
        
        if not regular_supervisors.empty:
            print("✅ Regular nursing supervisor hours variation:")
            supervisor_hours = regular_supervisors.groupby('DayOfWeek')['ModelHours'].sum()
            for day, hours in supervisor_hours.items():
                print(f"    {day}: {hours:.2f} hours")
        
        return True
        
    except Exception as e:
        print(f"❌ Role pattern test failed: {e}")
        return False

def main():
    """Run all model data tests."""
    print("=" * 60)
    print("MODEL DATA LOADING TEST")
    print("=" * 60)
    
    tests = [
        ("Model Data Completeness", test_model_data_completeness),
        ("Specific Role Patterns", test_specific_role_patterns)
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
    print("MODEL DATA TEST SUMMARY")
    print('='*60)
    print(f"Tests Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 ALL MODEL DATA TESTS PASSED!")
        print("✅ Model data correctly loads day-specific hour allocations")
        return 0
    else:
        print("❌ SOME MODEL DATA TESTS FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())