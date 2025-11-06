#!/bin/bash
# Pi Zero 2W ARM Performance Test Script
# 
# Runs performance benchmarks in a Docker container with ARM emulation
# and resource constraints matching Pi Zero 2W specifications.
#
# Pi Zero 2W Specs:
# - CPU: 1GHz quad-core ARM Cortex-A53 (ARMv8)
# - RAM: 512MB
# - Storage: SD card (slow I/O)
#
# Usage:
#   ./scripts/run_pi_perf_gate.sh [--output results.json]

set -e

# Default values
OUTPUT_FILE="${1:-pi_perf_results.json}"
WORKDIR="/app"
IMAGE="python:3.12-slim"
PLATFORM="linux/arm/v8"

# Resource constraints (Pi Zero 2W specs)
CPUS="1.0"           # Single core effective performance
MEMORY="512m"        # 512MB RAM
MEMORY_SWAP="512m"   # No swap to simulate constrained environment

echo "========================================"
echo "Pi Zero 2W Performance Gate"
echo "========================================"
echo "Platform: ${PLATFORM}"
echo "CPUs: ${CPUS}"
echo "Memory: ${MEMORY}"
echo "Output: ${OUTPUT_FILE}"
echo "========================================"
echo ""

# Create temporary directory for test
TEMP_DIR=$(mktemp -d)
trap "rm -rf ${TEMP_DIR}" EXIT

# Copy necessary files to temp directory
echo "📦 Preparing test environment..."
cp -r calendarbot_lite "${TEMP_DIR}/"
cp requirements.txt "${TEMP_DIR}/"
cp pyproject.toml "${TEMP_DIR}/"
cp setup.py "${TEMP_DIR}/" 2>/dev/null || true
cp tests/ci_performance_benchmark.py "${TEMP_DIR}/"
cp scripts/validate_pi_perf.py "${TEMP_DIR}/"

# Create a minimal setup.py if it doesn't exist
if [ ! -f "${TEMP_DIR}/setup.py" ]; then
    cat > "${TEMP_DIR}/setup.py" << 'EOF'
from setuptools import setup, find_packages

setup(
    name="calendarbot",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        line.strip()
        for line in open("requirements.txt")
        if line.strip() and not line.startswith("#")
    ],
)
EOF
fi

# Run benchmark in ARM Docker container with resource limits
echo "🚀 Running performance benchmark in ARM container..."
echo "   (This may take a few minutes on first run due to ARM emulation)"
echo ""

docker run --rm \
    --platform "${PLATFORM}" \
    --cpus="${CPUS}" \
    --memory="${MEMORY}" \
    --memory-swap="${MEMORY_SWAP}" \
    -v "${TEMP_DIR}:${WORKDIR}" \
    -w "${WORKDIR}" \
    "${IMAGE}" \
    bash -c "
        set -e
        echo '📥 Installing dependencies...'
        pip install --quiet --no-cache-dir --prefer-binary -e . psutil
        
        echo '⚡ Running 50-event benchmark...'
        python ci_performance_benchmark.py --run fifty --output benchmark_results.json
        
        echo ''
        echo '✅ Benchmark complete'
        cat benchmark_results.json
    " | tee "${TEMP_DIR}/docker_output.log"

# Copy results out of temp directory
cp "${TEMP_DIR}/benchmark_results.json" "${OUTPUT_FILE}"

echo ""
echo "========================================"
echo "📊 Performance Results"
echo "========================================"
cat "${OUTPUT_FILE}" | python -m json.tool

echo ""
echo "========================================"
echo "✅ Benchmark completed successfully"
echo "Results saved to: ${OUTPUT_FILE}"
echo "========================================"
