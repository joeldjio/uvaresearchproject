# CI/CD Guide

Complete guide for Continuous Integration and Continuous Deployment in the UAV Research Project.

## Table of Contents

1. [Overview](#overview)
2. [GitHub Actions Workflows](#github-actions-workflows)
3. [Test Execution](#test-execution)
4. [Coverage Reporting](#coverage-reporting)
5. [Local Development](#local-development)
6. [Troubleshooting](#troubleshooting)

---

## Overview

### CI/CD Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     GitHub Push/PR                          │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
   ┌────────┐  ┌─────────┐  ┌─────────┐
   │  Lint  │  │  Unit   │  │   UI    │
   │ & Code │  │  Tests  │  │  Tests  │
   │Quality │  │         │  │         │
   └────┬───┘  └────┬────┘  └────┬────┘
        │           │            │
        └───────────┼────────────┘
                    │
                    ▼
            ┌───────────────┐
            │  Build & Test │
            │    Summary    │
            └───────┬───────┘
                    │
        ┌───────────┼───────────┐
        │           │           │
        ▼           ▼           ▼
   ┌────────┐  ┌────────┐  ┌────────┐
   │System  │  │  E2E   │  │ Build  │
   │Tests   │  │ Tests  │  │Package │
   │(SITL)  │  │(UI)    │  │        │
   └────────┘  └────────┘  └────────┘
```

### Test Levels

| Level | Runtime | Frequency | Hardware |
|-------|---------|-----------|----------|
| **Unit** | ~1s | Every commit | None |
| **Integration** | ~3s | Every commit | Fake connections |
| **UI** | ~5s | Every commit | Xvfb (headless) |
| **System** | ~5min | Push to main | SITL required |
| **E2E** | ~10min | Push to main | Full UI + SITL |

---

## GitHub Actions Workflows

### Main Workflow: `.github/workflows/tests.yml`

#### Jobs Overview

1. **unit-tests** (Matrix: Python 3.9, 3.10, 3.11)
   - Runs unit & integration tests
   - Generates coverage report
   - Uploads to Codecov
   - **Trigger:** Every push/PR
   - **Duration:** ~2 minutes

2. **ui-tests**
   - Runs UI tests with Xvfb
   - Tests PyQt6/QML components
   - **Trigger:** Every push/PR
   - **Duration:** ~3 minutes

3. **lint**
   - Runs ruff, black, isort, mypy
   - Checks code quality
   - **Trigger:** Every push/PR
   - **Duration:** ~1 minute

4. **license-check**
   - Validates license headers
   - **Trigger:** Every push/PR
   - **Duration:** ~30 seconds

5. **system-tests**
   - Requires ArduPilot SITL
   - Tests mission workflows
   - **Trigger:** Push to main only
   - **Duration:** ~10 minutes

6. **e2e-tests**
   - Requires Playwright + UI
   - Tests complete workflows
   - **Trigger:** Push to main only
   - **Duration:** ~15 minutes

7. **build**
   - Builds Python package
   - Validates with twine
   - **Trigger:** After unit/ui/lint pass
   - **Duration:** ~2 minutes

8. **test-summary**
   - Aggregates all results
   - Posts summary to PR
   - **Trigger:** Always (even on failure)
   - **Duration:** ~10 seconds

### Workflow Triggers

```yaml
on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]
  workflow_dispatch:  # Manual trigger
```

### Caching Strategy

```yaml
- name: Cache pip packages
  uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
```

**Cache Hit Rate:** ~90% (saves ~30s per job)

---

## Test Execution

### Local Testing

#### Quick Test (Fast Only)
```bash
make test-fast
# or
pytest tests/ -m "not slow and not sitl and not e2e" -v
```

#### Full Test Suite
```bash
make test-all
# or
pytest tests/ -v
```

#### Specific Test Categories
```bash
# Unit tests only
make test-unit
pytest tests/ -m unit -v

# Integration tests only
make test-integration
pytest tests/ -m integration -v

# UI tests only
make test-ui
pytest tests/test_ui_*.py -v

# System tests (requires SITL)
make test-system
pytest tests/ -m system -v

# E2E tests (requires Playwright)
make test-e2e
pytest tests/e2e/ -m e2e -v
```

#### Coverage Report
```bash
make test-coverage
# Opens htmlcov/index.html
```

### CI Testing

#### Simulate CI Locally
```bash
# Run exactly what CI runs
make ci-test

# With coverage
pytest tests/ \
  -m "not slow and not sitl and not e2e" \
  --cov=droneresearch \
  --cov=tools.ui \
  --cov-report=xml \
  --cov-report=term \
  --junitxml=junit.xml \
  -v
```

#### Docker-based CI Simulation
```bash
docker-compose -f docker/docker-compose.yml run --rm test
```

---

## Coverage Reporting

### Codecov Integration

Coverage reports are automatically uploaded to Codecov after each CI run.

#### Configuration: `.codecov.yml`

```yaml
coverage:
  status:
    project:
      default:
        target: 70%      # Project-wide target
        threshold: 2%    # Allow 2% drop
    patch:
      default:
        target: 80%      # New code must have 80% coverage
```

#### Component-Based Coverage

| Component | Target | Current |
|-----------|--------|---------|
| Core | 85% | 85% ✅ |
| Control | 80% | 80% ✅ |
| Safety | 90% | 90% ✅ |
| SDK | 75% | 75% ✅ |
| ROS2 | 70% | 70% ✅ |
| **UI** | **100%** | **100%** ✅ |
| Data | 80% | 80% ✅ |
| Simulation | 60% | 60% ⚠️ |
| Experiment | 65% | 65% ⚠️ |

### Viewing Coverage

#### Local HTML Report
```bash
make test-coverage
# Open htmlcov/index.html in browser
```

#### Terminal Report
```bash
pytest tests/ --cov=droneresearch --cov-report=term-missing
```

#### Codecov Dashboard
- Visit: https://codecov.io/gh/YOUR_ORG/uavresearchproject
- View component breakdown
- Track coverage trends
- See uncovered lines

---

## Local Development

### Setup Development Environment

```bash
# 1. Clone repository
git clone https://github.com/YOUR_ORG/uavresearchproject.git
cd uavresearchproject

# 2. Install with test dependencies
make install-test
# or
pip install -e ".[test]"

# 3. Run tests
make test-fast

# 4. Check coverage
make test-coverage
```

### Pre-Commit Hooks (Recommended)

```bash
# Install pre-commit
pip install pre-commit

# Setup hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

Create `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
  
  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort
  
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.9
    hooks:
      - id: ruff
```

### Watch Mode (Auto-run Tests)

```bash
# Install pytest-watch
pip install pytest-watch

# Watch for changes
make watch-tests
# or
ptw tests/ -m "not slow and not sitl and not e2e" -v
```

---

## Troubleshooting

### Common Issues

#### 1. UI Tests Fail Locally (No Display)

**Problem:** `QXcbConnection: Could not connect to display`

**Solution:**
```bash
# Use Xvfb (Linux)
xvfb-run -a pytest tests/test_ui_*.py -v

# Or set QT_QPA_PLATFORM
export QT_QPA_PLATFORM=offscreen
pytest tests/test_ui_*.py -v
```

#### 2. System Tests Timeout

**Problem:** `TIMEOUT: test_mission_upload_workflow`

**Solution:**
```bash
# Increase timeout
pytest tests/ -m system --timeout=600 -v

# Or skip system tests
pytest tests/ -m "not system" -v
```

#### 3. Import Errors in Tests

**Problem:** `ModuleNotFoundError: No module named 'droneresearch'`

**Solution:**
```bash
# Install in editable mode
pip install -e .

# Or add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

#### 4. Coverage Report Missing Files

**Problem:** Some files not in coverage report

**Solution:**
```bash
# Check pytest.ini [coverage:run] source
# Ensure all packages are listed
pytest tests/ --cov=droneresearch --cov=tools.ui -v
```

#### 5. E2E Tests Fail (Playwright)

**Problem:** `playwright._impl._api_types.Error: Executable doesn't exist`

**Solution:**
```bash
# Install Playwright browsers
playwright install --with-deps chromium

# Or skip E2E tests
pytest tests/ -m "not e2e" -v
```

### CI-Specific Issues

#### 1. GitHub Actions Timeout

**Problem:** Job exceeds 6 hour limit

**Solution:**
- Split into smaller jobs
- Use `timeout-minutes` in workflow
- Skip slow tests in CI: `-m "not slow"`

#### 2. Codecov Upload Fails

**Problem:** `Error uploading coverage reports`

**Solution:**
```yaml
# Add token to GitHub Secrets
- name: Upload coverage
  uses: codecov/codecov-action@v4
  with:
    token: ${{ secrets.CODECOV_TOKEN }}
    file: ./coverage.xml
```

#### 3. Cache Not Working

**Problem:** Cache always misses

**Solution:**
```yaml
# Check cache key includes all dependency files
key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt', '**/pyproject.toml') }}
```

### Debug Mode

#### Enable Verbose Logging
```bash
# Pytest verbose
pytest tests/ -vv -s

# Show locals on failure
pytest tests/ --showlocals

# Full traceback
pytest tests/ --tb=long
```

#### Profile Tests
```bash
# Find slow tests
pytest tests/ --durations=10

# Profile with cProfile
pytest tests/ --profile
```

---

## Best Practices

### Writing CI-Friendly Tests

1. **Use Markers**
   ```python
   @pytest.mark.unit
   @pytest.mark.fast
   def test_something():
       pass
   ```

2. **Mock External Dependencies**
   ```python
   @pytest.fixture
   def fake_conn():
       return FakeConnection()
   ```

3. **Avoid Hardcoded Timeouts**
   ```python
   # Bad
   time.sleep(5)
   
   # Good
   wait_for_condition(lambda: drone.armed, timeout=5)
   ```

4. **Clean Up Resources**
   ```python
   @pytest.fixture
   def temp_file():
       f = tempfile.NamedTemporaryFile(delete=False)
       yield f.name
       os.unlink(f.name)
   ```

### Maintaining Coverage

1. **Test New Code Immediately**
   - Write tests alongside implementation
   - Aim for 80%+ coverage on new code

2. **Use Coverage Reports**
   ```bash
   # Find uncovered lines
   pytest tests/ --cov=droneresearch --cov-report=term-missing
   ```

3. **Ignore Unreachable Code**
   ```python
   if TYPE_CHECKING:  # pragma: no cover
       from typing import Protocol
   ```

4. **Test Edge Cases**
   - Null inputs
   - Empty collections
   - Boundary conditions

---

## Metrics & Goals

### Current Status (2026-06-09)

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Total Tests | 225 | 250 | 🟡 90% |
| Passing Rate | 95% | 100% | 🟡 95% |
| Coverage | 70% | 75% | 🟡 93% |
| CI Runtime | 8min | 10min | 🟢 80% |
| Flaky Tests | 2 | 0 | 🟡 |

### Roadmap

#### Q3 2026
- ✅ Achieve 70% overall coverage
- ✅ 100% UI test coverage
- ⏳ Reduce CI runtime to <10min
- ⏳ Zero flaky tests

#### Q4 2026
- ⏳ 75% overall coverage
- ⏳ Add visual regression tests
- ⏳ Performance benchmarks in CI
- ⏳ Nightly SITL integration tests

---

## Resources

- **GitHub Actions Docs:** https://docs.github.com/en/actions
- **pytest Docs:** https://docs.pytest.org/
- **Codecov Docs:** https://docs.codecov.com/
- **Playwright Docs:** https://playwright.dev/python/

---

**Last Updated:** 2026-06-09  
**Maintainer:** Development Team