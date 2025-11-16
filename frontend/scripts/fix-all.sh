#!/bin/bash
# Frontend Auto-Fix Script
# Automatically fixes formatting and linting issues

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$(dirname "$SCRIPT_DIR")"

cd "$FRONTEND_DIR"

echo "================================"
echo "Frontend Auto-Fix"
echo "================================"
echo ""

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
    echo ""
fi

echo "Step 1/3: Auto-formatting code with Prettier..."
npm run format
echo "✓ Code formatted"
echo ""

echo "Step 2/3: Auto-fixing JavaScript issues with ESLint..."
npm run lint:js:fix || true
echo "✓ JavaScript issues fixed (where possible)"
echo ""

echo "Step 3/3: Auto-fixing CSS issues with Stylelint..."
npm run lint:css:fix || true
echo "✓ CSS issues fixed (where possible)"
echo ""

echo "================================"
echo "Auto-fix complete!"
echo "Run 'npm run quality' to verify"
echo "================================"
