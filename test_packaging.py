#!/usr/bin/env python3
"""Test script to verify the enhanced packaging setup."""

import sys
import subprocess
from pathlib import Path

def test_package_imports():
    """Test that the package can be imported correctly."""
    try:
        # Test package import
        import calendarbot
        print(f"✅ Package import successful")
        print(f"   Version: {calendarbot.__version__}")
        print(f"   Description: {calendarbot.__description__}")
        
        # Test main module import
        from calendarbot import main
        print(f"✅ Main module import successful")
        
        # Test version consistency
        from calendarbot import __version__
        print(f"✅ Version accessible: {__version__}")
        
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_entry_points():
    """Test that entry points are configured correctly."""
    try:
        # Test main entry point
        from main import main_entry
        print(f"✅ Main entry point accessible")
        
        # Test calendarbot module entry point
        from calendarbot.__main__ import __name__ as main_name
        print(f"✅ Module entry point accessible")
        
        return True
    except ImportError as e:
        print(f"❌ Entry point error: {e}")
        return False

def test_configuration_structure():
    """Test that configuration files and directories exist."""
    project_root = Path(__file__).parent
    
    # Check essential files
    files_to_check = [
        "setup.py",
        "pyproject.toml", 
        "requirements.txt",
        "calendarbot/__init__.py",
        "calendarbot/__main__.py",
        "calendarbot/main.py",
        "config/config.yaml.example"
    ]
    
    all_exist = True
    for file_path in files_to_check:
        full_path = project_root / file_path
        if full_path.exists():
            print(f"✅ {file_path} exists")
        else:
            print(f"❌ {file_path} missing")
            all_exist = False
    
    return all_exist

def test_command_line_interface():
    """Test command line interface options."""
    try:
        # Test help command
        result = subprocess.run([sys.executable, "main.py", "--help"], 
                              capture_output=True, text=True, timeout=10)
        if "--setup" in result.stdout:
            print("✅ --setup option available in CLI")
        else:
            print("❌ --setup option not found in CLI")
            return False
        
        if "--version" in result.stdout:
            print("✅ --version option available in CLI")
        else:
            print("❌ --version option not found in CLI")
            return False
            
        return True
    except subprocess.TimeoutExpired:
        print("❌ CLI test timed out")
        return False
    except Exception as e:
        print(f"❌ CLI test error: {e}")
        return False

def main():
    """Run all packaging tests."""
    print("🧪 Testing Enhanced Calendar Bot Packaging Setup")
    print("=" * 60)
    
    tests = [
        ("Package Imports", test_package_imports),
        ("Entry Points", test_entry_points), 
        ("Configuration Structure", test_configuration_structure),
        ("Command Line Interface", test_command_line_interface),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 Testing {test_name}:")
        result = test_func()
        results.append((test_name, result))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary:")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All packaging tests passed! Ready for pip installation.")
        return 0
    else:
        print("⚠️  Some tests failed. Please review the setup.")
        return 1

if __name__ == "__main__":
    sys.exit(main())