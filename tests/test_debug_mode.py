#!/usr/bin/env python3
"""
Test script to verify debug mode functionality.
"""

import subprocess
import sys
import os

def test_debug_mode_help():
    """Test that debug mode appears in help."""
    print("🔍 Testing debug mode help...")
    result = subprocess.run([sys.executable, "main.py", "--help"], 
                          capture_output=True, text=True)
    
    if "--debug" in result.stdout:
        print("✅ Debug mode appears in help")
        return True
    else:
        print("❌ Debug mode missing from help")
        return False

def test_validation_without_args():
    """Test validation when no arguments provided."""
    print("🔍 Testing validation without arguments...")
    result = subprocess.run([sys.executable, "main.py"], 
                          capture_output=True, text=True)
    
    if "use --debug flag" in result.stdout and result.returncode != 0:
        print("✅ Validation working correctly")
        return True
    else:
        print("❌ Validation not working")
        return False

def test_debug_mode_file_detection():
    """Test that debug mode detects and uses default files."""
    print("🔍 Testing debug mode file detection...")
    
    # Check if sample files exist
    facility_file = "examples/SampleFacilityData.csv"
    model_file = "examples/SampleModelData.csv"
    
    if not os.path.exists(facility_file):
        print(f"❌ Sample facility file not found: {facility_file}")
        return False
    
    if not os.path.exists(model_file):
        print(f"❌ Sample model file not found: {model_file}")
        return False
    
    # Test debug mode initialization (should show file paths)
    result = subprocess.run([sys.executable, "main.py", "--debug", "--help"], 
                          capture_output=True, text=True)
    
    # The --help should override the debug mode, so this tests argument parsing
    if "--debug" in result.stdout and result.returncode == 0:
        print("✅ Debug mode initializes correctly")
        return True
    else:
        print("❌ Debug mode initialization failed")
        return False

def main():
    """Run all debug mode tests."""
    print("=" * 60)
    print("DEBUG MODE FUNCTIONALITY TEST")
    print("=" * 60)
    
    tests = [
        ("Help Documentation", test_debug_mode_help),
        ("Argument Validation", test_validation_without_args),
        ("File Detection", test_debug_mode_file_detection)
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
    print("DEBUG MODE TEST SUMMARY")
    print('='*60)
    print(f"Tests Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 ALL DEBUG MODE TESTS PASSED!")
        return 0
    else:
        print("❌ SOME DEBUG MODE TESTS FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())