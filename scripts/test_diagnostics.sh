#!/bin/sh
# Test Suite Diagnostics for CalendarBot using standard pytest
# This script helps identify the root causes of test execution issues

set -e

# Activate virtual environment
. venv/bin/activate

echo "🔍 CalendarBot Test Suite Diagnostics"
echo "===================================="

# Function to run command with timeout
run_with_timeout() {
    local timeout_duration="$1"
    shift
    echo "⏱️ Running with ${timeout_duration}s timeout: $*"
    timeout "$timeout_duration" "$@" 2>/dev/null || {
        exit_code=$?
        if [ $exit_code -eq 124 ]; then
            echo "❌ Command timed out after ${timeout_duration}s"
        fi
        return $exit_code
    }
}

# 1. Test Discovery Analysis
echo "\n📊 1. TEST DISCOVERY ANALYSIS"
echo "------------------------------"
echo "🔍 Collecting all tests..."
pytest --collect-only -q > /tmp/test_collection.txt 2>&1 || true

if [ -f /tmp/test_collection.txt ]; then
    total_collected=$(grep "collected.*items" /tmp/test_collection.txt | tail -1)
    echo "📝 $total_collected"

    # Show test distribution
    echo "📂 Test Distribution:"
    echo "   Unit tests: $(find tests/unit/ -name "test_*.py" 2>/dev/null | wc -l) files"
    echo "   Integration tests: $(find tests/integration/ -name "test_*.py" 2>/dev/null | wc -l) files"
    echo "   Browser tests: $(find tests/browser/ -name "test_*.py" 2>/dev/null | wc -l) files"
    echo "   E2E tests: $(find tests/e2e/ -name "test_*.py" 2>/dev/null | wc -l) files"
else
    echo "❌ Test collection failed"
fi

# 2. Configuration Check
echo "\n⚙️ 2. CONFIGURATION CHECK"
echo "-------------------------"
echo "📋 Pytest configuration:"
pytest --markers | grep -E "(unit|integration|browser|e2e|fast|slow)" || echo "   Custom markers not properly configured"

echo "📄 Config files found:"
[ -f pytest.ini ] && echo "   ✅ pytest.ini" || echo "   ❌ pytest.ini missing"
[ -f tests/conftest.py ] && echo "   ✅ tests/conftest.py" || echo "   ❌ tests/conftest.py missing"
[ -f tests/browser/conftest.py ] && echo "   ✅ tests/browser/conftest.py" || echo "   ❌ tests/browser/conftest.py missing"

# 3. Quick Smoke Test
echo "\n🚭 3. QUICK SMOKE TEST (Max 5 tests, 30s timeout)"
echo "------------------------------------------------"
echo "🧪 Running minimal test sample..."
run_with_timeout 30 pytest tests/ --maxfail=1 -x -q --tb=line --disable-warnings | head -10

# 4. Browser Test Health Check
echo "\n🌐 4. BROWSER TEST HEALTH CHECK"
echo "------------------------------"
if [ -d tests/browser/ ] && [ "$(find tests/browser/ -name "test_*.py" | wc -l)" -gt 0 ]; then
    echo "🔍 Checking browser test dependencies..."
    python -c "
try:
    import pyppeteer
    print('   ✅ pyppeteer available')
except ImportError:
    print('   ❌ pyppeteer not available')

try:
    import psutil
    print('   ✅ psutil available for process management')
except ImportError:
    print('   ❌ psutil not available')
"

    echo "🧪 Testing browser fixture creation (10s timeout)..."
    run_with_timeout 10 pytest tests/browser/ --collect-only -q >/dev/null 2>&1 && \
        echo "   ✅ Browser tests can be collected" || \
        echo "   ❌ Browser test collection failed"
else
    echo "   ⏭️ No browser tests found"
fi

# 5. Hanging Process Check
echo "\n🔍 5. HANGING PROCESS CHECK"
echo "-------------------------"
echo "🧹 Current test-related processes:"
pgrep -af "pytest|chrome.*--test-type" 2>/dev/null || echo "   ✅ No hanging test processes found"

# 6. Coverage Setup Check
echo "\n📈 6. COVERAGE SETUP CHECK"
echo "-------------------------"
echo "🔍 Coverage dependencies:"
python -c "
try:
    import coverage
    print('   ✅ coverage.py available')
except ImportError:
    print('   ❌ coverage.py not available')

try:
    import pytest_cov
    print('   ✅ pytest-cov available')
except ImportError:
    print('   ❌ pytest-cov not available')
"

# 7. Individual vs Full Suite Test
echo "\n🎯 7. INDIVIDUAL VS FULL SUITE COMPARISON"
echo "----------------------------------------"
if [ -d tests/unit/ ] && [ "$(find tests/unit/ -name "test_*.py" | wc -l)" -gt 0 ]; then
    echo "🧪 Testing unit tests individually vs in suite..."

    # Test one unit test file individually
    first_unit_test=$(find tests/unit/ -name "test_*.py" | head -1)
    if [ -n "$first_unit_test" ]; then
        echo "📝 Individual test: $first_unit_test"
        run_with_timeout 15 pytest "$first_unit_test" -v --tb=line --disable-warnings | grep -E "(PASSED|FAILED|ERROR)" | wc -l > /tmp/individual_count.txt

        echo "📝 Same test in unit suite:"
        run_with_timeout 30 pytest tests/unit/ --maxfail=5 -q --disable-warnings | grep -E "(PASSED|FAILED|ERROR)" | wc -l > /tmp/suite_count.txt

        individual_count=$(cat /tmp/individual_count.txt 2>/dev/null || echo "0")
        suite_count=$(cat /tmp/suite_count.txt 2>/dev/null || echo "0")

        echo "   Individual execution: $individual_count tests"
        echo "   Suite execution: $suite_count tests"

        if [ "$individual_count" -ne "$suite_count" ] && [ "$individual_count" -gt 0 ] && [ "$suite_count" -gt 0 ]; then
            echo "   ⚠️ Execution count discrepancy detected!"
        else
            echo "   ✅ Execution counts match"
        fi
    fi
fi

# 8. Recommendations
echo "\n💡 8. RECOMMENDATIONS"
echo "--------------------"
echo "🎯 To fix test suite issues:"
echo "   1. Use category-specific execution:"
echo "      pytest tests/unit/ -m 'unit or fast'     # Fast unit tests"
echo "      pytest tests/browser/ -m browser         # Browser tests only"
echo ""
echo "   2. Use enhanced shell scripts:"
echo "      ./scripts/run_coverage.sh unit           # Unit tests with timeout"
echo "      ./scripts/run_coverage.sh browser        # Browser tests with cleanup"
echo ""
echo "   3. For hanging issues:"
echo "      ./scripts/quick_kill.sh                  # Kill hanging processes"
echo ""
echo "   4. For coverage consistency:"
echo "      ./scripts/run_coverage.sh individual calendarbot.module_name"

echo "\n✅ Diagnostics complete!"
echo "📋 Check the output above for specific issues to address."
