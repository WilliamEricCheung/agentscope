#!/usr/bin/env bash

# Run tests script for NixOS Agent Environment
# Executes robustness evaluation tests in different environments

set -euo pipefail

# Default variables
TEST_ENVIRONMENT="testing"
TEST_TYPE="all"
VERBOSE=false
COVERAGE=false
PARALLEL=false
MAX_WORKERS=4

# Help function
show_help() {
    cat << EOF
Usage: $0 [OPTIONS]

Run robustness evaluation tests for multi-round planning agents.

OPTIONS:
    --env ENV       Test environment (basic|extended|minimal|full) [default: testing]
    --type TYPE     Test type (unit|integration|robustness|all) [default: all]
    --verbose       Enable verbose output
    --coverage      Generate coverage report
    --parallel      Run tests in parallel
    --workers NUM   Number of parallel workers [default: 4]
    --help          Show this help message

EXAMPLES:
    $0                          # Run all tests with default settings
    $0 --env extended           # Run tests in extended environment
    $0 --type robustness        # Run only robustness tests
    $0 --coverage --verbose     # Run with coverage and verbose output
    $0 --parallel --workers 8   # Run tests in parallel with 8 workers
EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --env)
            TEST_ENVIRONMENT="$2"
            shift 2
            ;;
        --type)
            TEST_TYPE="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --coverage)
            COVERAGE=true
            shift
            ;;
        --parallel)
            PARALLEL=true
            shift
            ;;
        --workers)
            MAX_WORKERS="$2"
            shift 2
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Check if we're in the right directory
if [[ ! -f "flake.nix" ]]; then
    echo "Error: This script must be run from the project root directory"
    echo "Please cd to the nixos-agent-env directory first"
    exit 1
fi

echo "🧪 Running robustness evaluation tests..."
echo "Environment: $TEST_ENVIRONMENT"
echo "Test type: $TEST_TYPE"
[[ "$VERBOSE" == "true" ]] && echo "Verbose: enabled"
[[ "$COVERAGE" == "true" ]] && echo "Coverage: enabled"
[[ "$PARALLEL" == "true" ]] && echo "Parallel: enabled ($MAX_WORKERS workers)"

# Set up test environment variables
export AGENT_TEST_ENVIRONMENT="$TEST_ENVIRONMENT"
export AGENT_TEST_TYPE="$TEST_TYPE"

# Build test command
TEST_COMMAND="python -m pytest"

# Add test selection based on type
case $TEST_TYPE in
    unit)
        TEST_COMMAND="$TEST_COMMAND tests/unit/"
        ;;
    integration)
        TEST_COMMAND="$TEST_COMMAND tests/integration/"
        ;;
    robustness)
        TEST_COMMAND="$TEST_COMMAND tests/robustness/"
        ;;
    all|*)
        TEST_COMMAND="$TEST_COMMAND tests/"
        ;;
esac

# Add verbose flag
[[ "$VERBOSE" == "true" ]] && TEST_COMMAND="$TEST_COMMAND -v"

# Add coverage flag
if [[ "$COVERAGE" == "true" ]]; then
    TEST_COMMAND="$TEST_COMMAND --cov=. --cov-report=term-missing"
    [[ "$VERBOSE" == "true" ]] && TEST_COMMAND="$TEST_COMMAND --cov-report=html"
fi

# Add parallel execution
if [[ "$PARALLEL" == "true" ]]; then
    TEST_COMMAND="$TEST_COMMAND -n $MAX_WORKERS"
fi

# Add additional pytest options
TEST_COMMAND="$TEST_COMMAND --tb=short --strict-markers"

echo "Executing: $TEST_COMMAND"

# Run tests
if command -v nix &> /dev/null; then
    # Use Nix development shell if available
    echo "Using Nix development environment..."
    nix develop --command bash -c "$TEST_COMMAND"
else
    # Fallback to direct execution (assumes dependencies are installed)
    echo "Using system Python environment..."
    eval "$TEST_COMMAND"
fi

# Check test results
if [[ $? -eq 0 ]]; then
    echo "✅ All tests passed successfully!"
    
    # Generate summary report
    echo ""
    echo "📊 Test Summary:"
    echo "- Environment: $TEST_ENVIRONMENT"
    echo "- Test type: $TEST_TYPE"
    echo "- Status: PASSED"
    
    if [[ "$COVERAGE" == "true" ]]; then
        echo "- Coverage report generated in htmlcov/ directory"
    fi
    
else
    echo "❌ Some tests failed!"
    echo "Please check the output above for details."
    exit 1
fi