# E2E Testing Setup Guide

End-to-end testing for the UAV Research Platform UI.

## Overview

The platform uses **pytest-qt** for E2E testing of the PyQt6/QML desktop application, not Playwright (which is for web apps).

## Architecture

```
E2E Test Stack:
┌─────────────────────────────────────┐
│  pytest + pytest-qt                 │
│  ├─ QApplication fixture            │
│  ├─ QTest for UI interaction        │
│  └─ Service Locator for contexts    │
└─────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│  PyQt6/QML UI Application           │
│  ├─ MainWindow                      │
│  ├─ QML Panels                      │
│  └─ Backend Contexts                │
└─────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│  Fake/Mock Backends                 │
│  ├─ FakeConnection                  │
│  ├─ FakeTelemetry                   │
│  └─ Mock Services                   │
└─────────────────────────────────────┘
```

## Installation

```bash
# Install test dependencies
pip install -e ".[test]"

# Verify pytest-qt is installed
pytest --co -q tests/e2e/
```

## Running E2E Tests

### All E2E Tests

```bash
# Run all E2E tests
pytest tests/e2e/ -m e2e -v

# With coverage
pytest tests/e2e/ -m e2e --cov=tools.ui -v
```

### Specific Test Files

```bash
# Qt-based E2E tests
pytest tests/e2e/test_qt_ui_workflows.py -v

# Playwright-based tests (web UI, if implemented)
pytest tests/e2e/test_ui_workflows.py -m e2e -v
```

### With Display

E2E tests require a display. On Linux without a display:

```bash
# Use Xvfb (virtual framebuffer)
xvfb-run -a pytest tests/e2e/ -m e2e -v

# Or set QT_QPA_PLATFORM
export QT_QPA_PLATFORM=offscreen
pytest tests/e2e/ -m e2e -v
```

## Test Structure

### Current E2E Tests

| Test File | Type | Tests | Status |
|-----------|------|-------|--------|
| `test_qt_ui_workflows.py` | pytest-qt | 10 | ✅ Active |
| `test_ui_workflows.py` | Playwright | 10 | ⏸️ Skipped (web UI) |

### Test Categories

1. **UI Startup & Navigation**
   - Window creation
   - Panel navigation
   - Layout rendering

2. **Drone Operations**
   - Connection workflow
   - ARM/DISARM
   - Telemetry updates

3. **Safety Features**
   - APF toggle
   - Geofence configuration
   - Collision avoidance

4. **Swarm Operations**
   - Formation selection
   - Multi-drone coordination
   - Leader-follower

5. **ROS2 Integration**
   - Bag recording
   - Bag playback
   - Topic monitoring

6. **Experiment Execution**
   - Script execution
   - Scenario running
   - Metrics collection

7. **Performance**
   - UI responsiveness
   - Telemetry throughput
   - Memory usage

## Writing E2E Tests

### Basic Template

```python
import pytest
from PyQt6.QtTest import QTest

@pytest.mark.e2e
@pytest.mark.ui
def test_my_workflow(qapp, wired_locator):
    """E2E: Description of workflow"""
    from tools.ui.main_window import MainWindow
    
    # Setup
    window = MainWindow()
    window.show()
    
    # Test workflow
    # ... your test code ...
    
    # Cleanup
    window.close()
```

### Using Contexts

```python
@pytest.mark.e2e
def test_with_contexts(qapp, wired_locator, fake_conn):
    """E2E: Test with service locator contexts"""
    # Get contexts
    swarm_ctx = wired_locator.get("swarm")
    safety_ctx = wired_locator.get("safety")
    
    # Setup drones
    swarm_ctx.add_drone("UAV_1", fake_conn)
    
    # Test workflow
    safety_ctx.toggle_apf()
    assert safety_ctx.apf_enabled is True
```

### Simulating User Input

```python
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest

# Click button
button = window.findChild(QPushButton, "armButton")
QTest.mouseClick(button, Qt.MouseButton.LeftButton)

# Type text
text_edit = window.findChild(QLineEdit, "portInput")
QTest.keyClicks(text_edit, "tcp:127.0.0.1:5760")

# Wait for UI update
QTest.qWait(100)  # Wait 100ms
```

### Verifying UI State

```python
# Check widget visibility
assert button.isVisible()
assert button.isEnabled()

# Check text content
assert label.text() == "ARMED"

# Check property values
assert window.property("currentPanel") == "map"
```

## Best Practices

### 1. Use Fixtures

```python
@pytest.fixture
def ui_with_drone(qapp, wired_locator, fake_conn):
    """Fixture: UI with connected drone"""
    from tools.ui.main_window import MainWindow
    
    swarm_ctx = wired_locator.get("swarm")
    swarm_ctx.add_drone("UAV_1", fake_conn)
    fake_conn.connected = True
    
    window = MainWindow()
    window.show()
    
    yield window, swarm_ctx
    
    window.close()
```

### 2. Wait for Async Operations

```python
# Bad: No wait
button.click()
assert label.text() == "Done"  # May fail

# Good: Wait for update
button.click()
QTest.qWait(100)
assert label.text() == "Done"
```

### 3. Clean Up Resources

```python
@pytest.mark.e2e
def test_with_cleanup(qapp):
    window = MainWindow()
    window.show()
    
    try:
        # Test code
        pass
    finally:
        # Always cleanup
        window.close()
```

### 4. Use Markers

```python
@pytest.mark.e2e          # E2E test
@pytest.mark.ui           # Requires UI
@pytest.mark.slow         # Takes >1s
@pytest.mark.skip_ci      # Skip in CI
```

## Troubleshooting

### Issue: "QXcbConnection: Could not connect to display"

**Solution:**
```bash
# Use Xvfb
xvfb-run -a pytest tests/e2e/ -m e2e -v

# Or offscreen platform
export QT_QPA_PLATFORM=offscreen
pytest tests/e2e/ -m e2e -v
```

### Issue: "QApplication instance already exists"

**Solution:**
```python
# Use qapp fixture, don't create QApplication manually
def test_my_test(qapp):  # qapp fixture provides QApplication
    # Don't do: app = QApplication([])
    pass
```

### Issue: Tests hang or timeout

**Solution:**
```python
# Add timeout marker
@pytest.mark.timeout(30)
def test_slow_operation(qapp):
    pass

# Or use QTest.qWait() instead of time.sleep()
QTest.qWait(1000)  # Wait 1 second
```

### Issue: "Cannot access attribute 'engine'"

**Solution:**
```python
# Check if MainWindow has the attribute
if hasattr(window, 'engine'):
    engine = window.engine
else:
    # Alternative approach
    pass
```

## CI/CD Integration

### GitHub Actions

E2E tests run in CI with Xvfb:

```yaml
- name: Run E2E tests
  run: |
    xvfb-run -a pytest tests/e2e/ -m e2e --video=retain-on-failure -v
  timeout-minutes: 15
```

### Local CI Simulation

```bash
# Simulate CI environment
docker run -it --rm \
  -v $(pwd):/app \
  -w /app \
  python:3.11 \
  bash -c "
    apt-get update && apt-get install -y xvfb libxcb-xinerama0
    pip install -e '.[test]'
    xvfb-run -a pytest tests/e2e/ -m e2e -v
  "
```

## Performance Benchmarks

### Target Metrics

| Metric | Target | Current |
|--------|--------|---------|
| UI Startup | <2s | TBD |
| Panel Switch | <100ms | TBD |
| Telemetry Update | <50ms | TBD |
| Formation Preview | <200ms | TBD |

### Measuring Performance

```python
@pytest.mark.e2e
@pytest.mark.slow
def test_performance_metric(qapp):
    import time
    
    start = time.time()
    # ... operation ...
    duration = (time.time() - start) * 1000  # ms
    
    assert duration < 2000, f"Too slow: {duration}ms"
```

## Future Enhancements

### Planned Features

1. **Visual Regression Testing**
   - Screenshot comparison
   - Pixel-perfect UI validation
   - Automated visual diffs

2. **Accessibility Testing**
   - Keyboard navigation
   - Screen reader compatibility
   - WCAG compliance

3. **Load Testing**
   - 100+ drones
   - High-frequency telemetry
   - Memory profiling

4. **Integration with Real Hardware**
   - SITL integration
   - Hardware-in-the-loop
   - Real drone testing

## Resources

- **pytest-qt Docs:** https://pytest-qt.readthedocs.io/
- **PyQt6 Docs:** https://www.riverbankcomputing.com/static/Docs/PyQt6/
- **QTest Docs:** https://doc.qt.io/qt-6/qtest.html

---

**Last Updated:** 2026-06-09  
**Maintainer:** Development Team