#!/usr/bin/env python3
"""Diagnostic script to identify missing dependencies and import issues."""

import sys
import importlib.util

def test_import(module_name, description):
    """Test if a module can be imported."""
    try:
        spec = importlib.util.find_spec(module_name)
        if spec is None:
            print(f"❌ {description}: Module '{module_name}' not found")
            return False
        
        # Try actual import
        module = importlib.import_module(module_name)
        print(f"✅ {description}: Module '{module_name}' imported successfully")
        return True
    except Exception as e:
        print(f"❌ {description}: Failed to import '{module_name}' - {e}")
        return False

def test_performance_dependencies():
    """Test dependencies specifically needed by performance monitoring."""
    print("=== Testing Performance Monitoring Dependencies ===")
    
    deps = [
        ("psutil", "System and process utilities (required by performance monitoring)"),
        ("threading", "Threading support (built-in)"),
        ("json", "JSON serialization (built-in)"),
        ("uuid", "UUID generation (built-in)"),
        ("pathlib", "Path utilities (built-in)"),
        ("dataclasses", "Dataclass support (built-in)"),
        ("enum", "Enum support (built-in)"),
        ("contextlib", "Context managers (built-in)"),
        ("functools", "Function utilities (built-in)"),
        ("datetime", "Date/time utilities (built-in)"),
        ("logging", "Logging framework (built-in)"),
        ("logging.handlers", "Advanced logging handlers (built-in)")
    ]
    
    success_count = 0
    total_count = len(deps)
    
    for module_name, description in deps:
        if test_import(module_name, description):
            success_count += 1
    
    print(f"\nDependency Test Results: {success_count}/{total_count} successful")
    return success_count == total_count

def test_calendarbot_modules():
    """Test CalendarBot module imports."""
    print("\n=== Testing CalendarBot Module Imports ===")
    
    # Add current directory to path to import local modules
    sys.path.insert(0, '.')
    
    modules = [
        ("calendarbot.utils.logging", "Enhanced logging utilities"),
        ("calendarbot.monitoring.performance", "Performance monitoring (should fail due to psutil)"),
        ("calendarbot.monitoring", "Monitoring module init"),
        ("calendarbot.structured.logging", "Structured logging"),
        ("calendarbot.security.logging", "Security logging"),
        ("calendarbot.optimization.production", "Production optimization"),
        ("calendarbot.cache.manager", "Cache manager (should fail due to monitoring dependency)"),
    ]
    
    success_count = 0
    total_count = len(modules)
    
    for module_name, description in modules:
        if test_import(module_name, description):
            success_count += 1
    
    print(f"\nModule Import Test Results: {success_count}/{total_count} successful")
    return success_count == total_count

def test_requirements_coverage():
    """Check if requirements.txt covers needed dependencies."""
    print("\n=== Analyzing Requirements Coverage ===")
    
    try:
        with open('requirements.txt', 'r') as f:
            requirements = f.read()
        
        required_packages = [
            'psutil',  # Missing - needed for performance monitoring
        ]
        
        missing_packages = []
        for package in required_packages:
            if package not in requirements.lower():
                missing_packages.append(package)
        
        if missing_packages:
            print(f"❌ Missing packages in requirements.txt: {', '.join(missing_packages)}")
            return False
        else:
            print("✅ All required packages found in requirements.txt")
            return True
            
    except FileNotFoundError:
        print("❌ requirements.txt not found")
        return False

def main():
    """Run all diagnostic tests."""
    print("CalendarBot Launch Diagnostic Tool")
    print("==================================")
    
    print("Testing environment and dependencies...\n")
    
    # Test basic dependencies
    deps_ok = test_performance_dependencies()
    
    # Test module imports
    modules_ok = test_calendarbot_modules()
    
    # Test requirements coverage
    reqs_ok = test_requirements_coverage()
    
    print("\n=== DIAGNOSTIC SUMMARY ===")
    print(f"Dependencies: {'✅ PASS' if deps_ok else '❌ FAIL'}")
    print(f"Module Imports: {'✅ PASS' if modules_ok else '❌ FAIL'}")
    print(f"Requirements Coverage: {'✅ PASS' if reqs_ok else '❌ FAIL'}")
    
    if not deps_ok or not modules_ok or not reqs_ok:
        print("\n🔧 RECOMMENDED FIXES:")
        if not reqs_ok:
            print("1. Add missing dependencies to requirements.txt")
            print("   - Add 'psutil>=5.9.0' to requirements.txt")
        if not deps_ok:
            print("2. Install missing dependencies:")
            print("   - Run: pip install psutil")
        if not modules_ok:
            print("3. Fix module import chain after dependencies are resolved")
        
        print("\n📋 NEXT STEPS:")
        print("1. Update requirements.txt with missing dependencies")
        print("2. Install dependencies in virtual environment")
        print("3. Re-test application startup")
    else:
        print("\n✅ All tests passed - application should start successfully")

if __name__ == "__main__":
    main()