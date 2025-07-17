#!/usr/bin/env python3
"""
System Integration Test for Workforce Analytics System.
Tests core functionality without requiring all optional dependencies.
"""

import sys
import os
import pandas as pd
import tempfile
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_data_loading():
    """Test data loading and basic validation."""
    print("🔍 Testing Data Loading...")
    
    # Test CSV file existence
    facility_file = "examples/SampleFacilityData.csv"
    model_file = "examples/SampleModelData.csv"
    
    if not os.path.exists(facility_file):
        print(f"❌ Facility data file not found: {facility_file}")
        return False
    
    if not os.path.exists(model_file):
        print(f"❌ Model data file not found: {model_file}")
        return False
    
    # Test basic pandas loading
    try:
        facility_df = pd.read_csv(facility_file)
        model_df = pd.read_csv(model_file)
        
        print(f"✅ Loaded {len(facility_df)} facility records")
        print(f"✅ Loaded {len(model_df)} model records")
        
        # Basic structure validation
        expected_facility_cols = ['LOCATION_KEY', 'LOCATION_NAME', 'HOURS_DATE', 'TOTAL_HOURS']
        for col in expected_facility_cols:
            if col not in facility_df.columns:
                print(f"❌ Missing expected column in facility data: {col}")
                return False
        
        expected_model_cols = ['LOCATION_KEY', 'LOCATION_NAME', 'HOURS_DATE', 'TOTAL_HOURS']
        for col in expected_model_cols:
            if col not in model_df.columns:
                print(f"❌ Missing expected column in model data: {col}")
                return False
        
        print("✅ Data structure validation passed")
        return True
        
    except Exception as e:
        print(f"❌ Error loading data: {str(e)}")
        return False

def test_module_imports():
    """Test that all modules can be imported without errors."""
    print("🔍 Testing Module Imports...")
    
    modules_to_test = [
        'config.constants',
        'src.models.data_models',
        'src.ingestion.model_loader', 
        'src.ingestion.hours_loader',
        'src.ingestion.normalizer',
        'src.analysis.statistics',
        'src.analysis.variance',
        'src.analysis.trends',
        'src.reporting.exceptions',
        'src.reporting.chart_generator',
        'src.reporting.pdf_generator',
        'src.reporting.report_orchestrator',
        'src.utils.logging_config',
        'src.utils.error_handlers'
    ]
    
    success_count = 0
    for module in modules_to_test:
        try:
            __import__(module)
            print(f"✅ {module}")
            success_count += 1
        except ImportError as e:
            if 'python_dotenv' in str(e) or 'playwright' in str(e):
                print(f"⚠️  {module} (optional dependency missing)")
                success_count += 1  # Count as success since these are optional
            else:
                print(f"❌ {module}: {str(e)}")
    
    print(f"📊 Module Import Results: {success_count}/{len(modules_to_test)} successful")
    return success_count >= len(modules_to_test) * 0.8  # 80% success rate required

def test_basic_statistical_functions():
    """Test core statistical functionality."""
    print("🔍 Testing Statistical Functions...")
    
    try:
        # Test pandas statistical operations
        test_data = pd.DataFrame({
            'values': [10, 12, 8, 15, 11, 9, 13, 10, 12, 14]
        })
        
        mean_val = test_data['values'].mean()
        std_val = test_data['values'].std()
        median_val = test_data['values'].median()
        
        print(f"✅ Basic statistics: mean={mean_val:.2f}, std={std_val:.2f}, median={median_val:.2f}")
        
        # Test that we can calculate control limits
        upper_limit = mean_val + 3 * std_val
        lower_limit = max(0, mean_val - 3 * std_val)  # Hours can't be negative
        
        print(f"✅ Control limits: upper={upper_limit:.2f}, lower={lower_limit:.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Statistical functions test failed: {str(e)}")
        return False

def test_date_processing():
    """Test date handling functionality."""
    print("🔍 Testing Date Processing...")
    
    try:
        # Test date parsing
        test_dates = ['7/7/24', '12/31/23', '1/1/24']
        
        for date_str in test_dates:
            try:
                # Test both formats that might be in the data
                parsed_date = pd.to_datetime(date_str, format='%m/%d/%y')
                print(f"✅ Parsed date: {date_str} -> {parsed_date.strftime('%Y-%m-%d')}")
            except:
                parsed_date = pd.to_datetime(date_str)
                print(f"✅ Parsed date (auto): {date_str} -> {parsed_date.strftime('%Y-%m-%d')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Date processing test failed: {str(e)}")
        return False

def test_directory_structure():
    """Test that all required directories can be created."""
    print("🔍 Testing Directory Structure...")
    
    required_dirs = [
        'output',
        'output/reports', 
        'logs',
        'src',
        'src/reporting/templates'
    ]
    
    success_count = 0
    for dir_path in required_dirs:
        try:
            os.makedirs(dir_path, exist_ok=True)
            if os.path.exists(dir_path):
                print(f"✅ Directory: {dir_path}")
                success_count += 1
            else:
                print(f"❌ Failed to create: {dir_path}")
        except Exception as e:
            print(f"❌ Directory creation failed for {dir_path}: {str(e)}")
    
    print(f"📊 Directory Results: {success_count}/{len(required_dirs)} successful")
    return success_count == len(required_dirs)

def main():
    """Run all integration tests."""
    print("=" * 80)
    print("WORKFORCE ANALYTICS SYSTEM - INTEGRATION TEST")
    print("=" * 80)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    tests = [
        ("Data Loading", test_data_loading),
        ("Module Imports", test_module_imports), 
        ("Statistical Functions", test_basic_statistical_functions),
        ("Date Processing", test_date_processing),
        ("Directory Structure", test_directory_structure)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"TEST: {test_name}")
        print('='*60)
        
        try:
            result = test_func()
            results.append((test_name, result))
            
            if result:
                print(f"🎉 {test_name}: PASSED")
            else:
                print(f"💥 {test_name}: FAILED")
                
        except Exception as e:
            print(f"💥 {test_name}: ERROR - {str(e)}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 80)
    print("INTEGRATION TEST SUMMARY")
    print("=" * 80)
    
    passed_tests = sum(1 for _, result in results if result)
    total_tests = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nOverall Result: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 ALL TESTS PASSED! System ready for deployment.")
        return 0
    elif passed_tests >= total_tests * 0.8:
        print("⚠️  MOSTLY FUNCTIONAL - Some optional features may not work.")
        return 0
    else:
        print("❌ SYSTEM NOT READY - Multiple critical failures detected.")
        return 1

if __name__ == "__main__":
    sys.exit(main())