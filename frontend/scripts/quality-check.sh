#!/bin/bash
# Frontend Code Quality Check Script
# Runs all quality checks: formatting and linting

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$(dirname "$SCRIPT_DIR")"

cd "$FRONTEND_DIR"

echo "================================"
echo "Frontend Code Quality Check"
echo "================================"
echo ""

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
    echo ""
fi

echo "Step 1/3: Checking code formatting with Prettier..."
npm run format:check
echo "✓ Formatting check passed"
echo ""

echo "Step 2/3: Linting JavaScript with ESLint..."
npm run lint:js
echo "✓ JavaScript lint check passed"
echo ""

echo "Step 3/3: Linting CSS with Stylelint..."
npm run lint:css
echo "✓ CSS lint check passed"
echo ""

echo "================================"
echo "All quality checks passed!"
echo "================================"
