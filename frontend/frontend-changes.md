# Frontend Code Quality Tools Implementation

This document describes the code quality tools added to the frontend development workflow.

## Overview

Essential code quality tools have been integrated into the frontend to ensure consistent formatting and catch potential issues. The toolchain includes:

- **Prettier** - Automatic code formatting for JavaScript, HTML, CSS, and JSON
- **ESLint** - JavaScript linting for code quality and best practices
- **Stylelint** - CSS linting for style consistency
- **EditorConfig** - Cross-editor configuration for consistent settings

## Files Added

### Configuration Files

1. **`package.json`** - NPM package configuration with all dev dependencies and scripts
2. **`.prettierrc`** - Prettier formatting rules
3. **`.prettierignore`** - Files to exclude from formatting
4. **`.eslintrc.json`** - ESLint rules for JavaScript
5. **`.eslintignore`** - Files to exclude from JavaScript linting
6. **`.stylelintrc.json`** - Stylelint rules for CSS
7. **`.stylelintignore`** - Files to exclude from CSS linting
8. **`.editorconfig`** - Editor-agnostic formatting settings

### Development Scripts

Located in `frontend/scripts/`:

1. **`quality-check.sh`** - Run all quality checks (format check + lint)
2. **`format-code.sh`** - Automatically format all code
3. **`fix-all.sh`** - Auto-fix formatting and linting issues

## Available NPM Scripts

```bash
# Formatting
npm run format          # Auto-format all code
npm run format:check    # Check formatting without changing files

# JavaScript Linting
npm run lint:js         # Check JavaScript for issues
npm run lint:js:fix     # Auto-fix JavaScript issues

# CSS Linting
npm run lint:css        # Check CSS for issues
npm run lint:css:fix    # Auto-fix CSS issues

# Combined Commands
npm run lint            # Run all linting (JS + CSS)
npm run lint:fix        # Fix all linting issues
npm run quality         # Full quality check (format + lint)
npm run quality:fix     # Fix all issues (format + lint)
```

## Quick Start

1. Install dependencies:
   ```bash
   cd frontend
   npm install
   ```

2. Run quality checks:
   ```bash
   npm run quality
   ```

3. Auto-fix all issues:
   ```bash
   npm run quality:fix
   ```

Or use the shell scripts:
```bash
./scripts/quality-check.sh    # Check everything
./scripts/format-code.sh      # Format code
./scripts/fix-all.sh          # Fix all issues
```

## Code Formatting Standards

### JavaScript (Prettier + ESLint)
- Double quotes for strings
- Semicolons required
- 2-space indentation
- 100-character line width
- ES5 trailing commas
- Curly braces required for all blocks
- No `var` declarations (use `const`/`let`)
- Prefer `const` over `let`
- Strict equality (`===`)

### CSS (Prettier + Stylelint)
- 2-space indentation
- Long-form hex colors (e.g., `#ffffff`)
- Legacy color function notation
- Consistent spacing and empty lines

### HTML (Prettier)
- 2-space indentation
- Consistent attribute formatting

## Code Changes Made

The following improvements were made to existing code:

### script.js
- Added curly braces to single-line `if` statements for consistency
- Fixed unused variable warnings by prefixing with underscore (`_index`)
- Removed debug `console.log` statements
- Applied consistent formatting throughout

### style.css
- Applied consistent indentation and spacing
- Added required empty lines between rules
- Standardized quote usage in font-family declarations

### index.html
- Applied consistent formatting and indentation

## Integration with Development Workflow

### Pre-commit Checks (Recommended)
Before committing code, run:
```bash
npm run quality
```

This ensures all code meets formatting and quality standards.

### Continuous Integration
Add to your CI pipeline:
```bash
cd frontend && npm ci && npm run quality
```

### Editor Integration

With `.editorconfig`, most editors will automatically:
- Use 2-space indentation
- Use LF line endings
- Trim trailing whitespace
- Insert final newlines

For enhanced support:
- **VS Code**: Install Prettier and ESLint extensions
- **WebStorm/IntelliJ**: Built-in support for all tools
- **Sublime Text**: Install EditorConfig and SublimeLinter packages

## Dependencies Installed

```json
{
  "prettier": "^3.3.0",
  "eslint": "^8.57.0",
  "eslint-config-prettier": "^9.1.0",
  "stylelint": "^16.6.0",
  "stylelint-config-standard": "^36.0.0"
}
```

## Maintenance

### Updating Rules
- Edit `.prettierrc` for formatting preferences
- Edit `.eslintrc.json` for JavaScript rules
- Edit `.stylelintrc.json` for CSS rules

### Adding New Rules
1. Install any additional ESLint/Stylelint plugins via npm
2. Add them to the respective config files
3. Run `npm run quality:fix` to apply new rules

### Regenerating node_modules
If issues arise:
```bash
rm -rf node_modules package-lock.json
npm install
```
