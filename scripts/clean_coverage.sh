#!/bin/bash
# Clean all coverage data files
# Run this if you see: "Can't combine statement coverage data with branch data"

echo "Cleaning coverage data files..."

# Remove all .coverage files
find . -name ".coverage*" -type f -exec rm -f {} \;

# Remove coverage reports
rm -rf htmlcov/
rm -f coverage.xml
rm -f coverage.json

echo "✅ Coverage data cleaned"
echo ""
echo "You can now run your tests without coverage conflicts:"
echo "  pytest tests/lite/ -m smoke -v"
echo "  python tests/ci_test_runner.py --critical-path"
