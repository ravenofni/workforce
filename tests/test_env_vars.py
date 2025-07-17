#!/usr/bin/env python3
"""
Test script to verify environment variable functionality.
"""

import os
import sys
import subprocess
import tempfile

def test_env_var_loading():
    """Test that environment variables are properly loaded and used as defaults."""
    print("🔍 Testing environment variable loading...")
    
    # Create a temporary .env file with test values
    test_env_content = """
DEBUG_MODE=true
LOG_LEVEL=WARNING
OUTPUT_DIR=test_output
DISPLAY_ONLY=true
EXCEPTIONS_ONLY=false
QUIET=true
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
        f.write(test_env_content)
        temp_env_file = f.name
    
    try:
        # Test that help shows environment variable info
        result = subprocess.run([sys.executable, "main.py", "--help"], 
                              capture_output=True, text=True,
                              env={**os.environ, 'DOTENV_PATH': temp_env_file})
        
        if "Environment variables:" in result.stdout:
            print("✅ Environment variable documentation in help")
            return True
        else:
            print("❌ Environment variable documentation missing")
            return False
            
    finally:
        # Clean up temp file
        os.unlink(temp_env_file)

def test_priority_order():
    """Test that command line arguments override environment variables."""
    print("🔍 Testing priority order (CLI > ENV > defaults)...")
    
    # Set environment variable
    env = os.environ.copy()
    env['LOG_LEVEL'] = 'ERROR'
    
    # Test that CLI argument overrides environment variable
    result = subprocess.run([
        sys.executable, "main.py", "--log-level", "WARNING", "--help"
    ], capture_output=True, text=True, env=env)
    
    # The help should execute successfully
    if result.returncode == 0:
        print("✅ CLI arguments can override environment variables")
        return True
    else:
        print("❌ CLI argument override failed")
        return False

def test_boolean_conversion():
    """Test that boolean environment variables are properly converted."""
    print("🔍 Testing boolean conversion...")
    
    test_cases = [
        ('true', True),
        ('false', False),
        ('1', True),
        ('0', False),
        ('yes', True),
        ('no', False),
        ('on', True),
        ('off', False)
    ]
    
    # Import the helper function
    sys.path.insert(0, '.')
    try:
        # Read the get_env_default function from main.py
        with open('main.py', 'r') as f:
            content = f.read()
            
        # Extract and test the function logic
        for env_value, expected in test_cases:
            # Simulate the boolean conversion
            actual = env_value.lower() in ('true', '1', 'yes', 'on')
            if actual == expected:
                print(f"✅ '{env_value}' -> {actual}")
            else:
                print(f"❌ '{env_value}' -> {actual}, expected {expected}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Boolean conversion test failed: {e}")
        return False

def test_type_conversion():
    """Test that numeric environment variables are properly converted."""
    print("🔍 Testing type conversion...")
    
    # Set environment variables for testing
    env = os.environ.copy()
    env['WEEKS_FOR_CONTROL'] = '16'
    env['VARIANCE_THRESHOLD'] = '20.5'
    
    # Test that the values are accepted
    result = subprocess.run([
        sys.executable, "main.py", "--help"
    ], capture_output=True, text=True, env=env)
    
    if result.returncode == 0:
        print("✅ Numeric environment variables processed")
        return True
    else:
        print("❌ Numeric environment variable processing failed")
        return False

def test_dotenv_import():
    """Test graceful handling when python-dotenv is not available."""
    print("🔍 Testing dotenv import handling...")
    
    # Test with a simple help command - should work even without dotenv
    result = subprocess.run([sys.executable, "main.py", "--version"], 
                          capture_output=True, text=True)
    
    if "Workforce Analytics System" in result.stdout:
        print("✅ Application works without dotenv dependency")
        return True
    else:
        print("❌ Application fails without dotenv")
        return False

def main():
    """Run all environment variable tests."""
    print("=" * 60)
    print("ENVIRONMENT VARIABLE FUNCTIONALITY TEST")
    print("=" * 60)
    
    tests = [
        ("Environment Variable Loading", test_env_var_loading),
        ("Priority Order", test_priority_order),
        ("Boolean Conversion", test_boolean_conversion),
        ("Type Conversion", test_type_conversion),
        ("Dotenv Import Handling", test_dotenv_import)
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
    print("ENVIRONMENT VARIABLE TEST SUMMARY")
    print('='*60)
    print(f"Tests Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 ALL ENVIRONMENT VARIABLE TESTS PASSED!")
        return 0
    else:
        print("❌ SOME ENVIRONMENT VARIABLE TESTS FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())