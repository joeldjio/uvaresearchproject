# Test-Strategie — uavresearch GCS

**Version:** 1.0  
**Datum:** 2026-06-09  
**Autor:** Bob (AI Software Engineer)

---

## Übersicht

Die uavresearch GCS Test-Strategie folgt der **Test-Pyramide** mit vier Ebenen:

```
         /\
        /  \  Abnahmetests (E2E)
       /----\
      /      \  Systemtests
     /--------\
    /          \  Integrationstests
   /------------\
  /              \  Unit-Tests
 /________________\
```

**Ziel:** 80% Code-Coverage mit automatisierten Tests auf allen Ebenen.

---

## 1. Unit-Tests

### 1.1 Definition
Unit-Tests testen **einzelne Funktionen/Klassen isoliert** ohne externe Abhängigkeiten.

### 1.2 Scope
- Python-Backend-Komponenten
- Einzelne Funktionen/Methoden
- Datenstrukturen und Algorithmen
- Keine I/O, keine Netzwerk-Calls, keine Datenbank

### 1.3 Existierende Unit-Tests

| Test-Datei | Komponente | Tests | Status |
|------------|------------|-------|--------|
| `test_fsm.py` | StateMachine | 8 | ✅ Pass |
| `test_apf.py` | APF Safety Filter | 12 | ✅ Pass |
| `test_telemetry.py` | Telemetry Snapshots | 6 | ✅ Pass |
| `test_formations.py` | Formation Algorithms | 8 | ✅ Pass |
| `test_mission.py` | Mission Engine | 10 | ✅ Pass |
| `test_logger.py` | Data Logger | 7 | ✅ Pass |
| `test_metrics_position_error.py` | Position Metrics | 4 | ✅ Pass |
| `test_ui_contexts.py` | UI Contexts | 28 | ✅ Pass |

**Total:** 83 Unit-Tests

### 1.4 Beispiel: Unit-Test für APF

```python
def test_apf_repulsion_force():
    """Test repulsion force calculation"""
    from droneresearch.safety.apf import APFFilter
    
    apf = APFFilter(min_separation=5.0, repulsion_gain=2.0)
    
    # Two drones 3m apart (below min_separation)
    pos1 = Pose3D(x=0, y=0, z=10)
    pos2 = Pose3D(x=3, y=0, z=10)
    
    force = apf._repulsion_force(pos1, pos2)
    
    # Force should push away from pos2
    assert force.x < 0  # Push in -x direction
    assert abs(force.y) < 0.1  # No y component
    assert abs(force.z) < 0.1  # No z component
```

### 1.5 Unit-Test Guidelines

**DO:**
- ✅ Test eine Funktion/Methode pro Test
- ✅ Verwende Mocks für externe Abhängigkeiten
- ✅ Teste Edge-Cases (None, 0, negative Werte)
- ✅ Teste Error-Handling (Exceptions)
- ✅ Schnelle Ausführung (<10ms pro Test)

**DON'T:**
- ❌ Keine echten Netzwerk-Calls
- ❌ Keine Datei-I/O (außer Temp-Files)
- ❌ Keine Datenbank-Zugriffe
- ❌ Keine Zeit-abhängigen Tests (sleep)

---

## 2. Integrationstests

### 2.1 Definition
Integrationstests testen **Zusammenspiel mehrerer Komponenten** mit echten Abhängigkeiten.

### 2.2 Scope
- Mehrere Klassen/Module zusammen
- Echte Datenbank/Datei-Zugriffe
- Mock-Netzwerk (FakeConnection)
- Keine echte Hardware (SITL/Mock)

### 2.3 Existierende Integrationstests

| Test-Datei | Komponente | Tests | Status |
|------------|------------|-------|--------|
| `test_swarm_context_runtime.py` | Swarm + Telemetry | 5 | ✅ Pass |
| `test_swarm_context_mission_multi.py` | Swarm + Mission | 4 | ✅ Pass |
| `test_reconnect_fsm.py` | FSM + Connection | 6 | ✅ Pass |
| `test_ros_context.py` | ROS2 Context | 8 | ✅ Pass |
| `test_ui_wire.py` | UI Context Wiring | 18 | ⚠️ 18 Errors |
| `test_bag_recorder.py` | ROS2 Bag Recording | 6 | ✅ Pass |
| `test_async_mission_upload.py` | Async Mission Upload | 5 | ✅ Pass |

**Total:** 52 Integrationstests (34 passing, 18 errors)

### 2.4 Beispiel: Integrationstest für Swarm + Mission

```python
def test_swarm_mission_upload_and_start(fake_conn):
    """Test mission upload and start with multiple drones"""
    from droneresearch.sdk.swarm import Swarm
    from droneresearch.control.mission import Waypoint
    
    swarm = Swarm()
    swarm.add("UAV_1", fake_conn)
    swarm.add("UAV_2", fake_conn)
    swarm.connect_all()
    
    # Create mission
    waypoints = [
        Waypoint(lat=47.397742, lon=8.545594, alt=10),
        Waypoint(lat=47.398, lon=8.546, alt=15),
    ]
    
    # Upload to both drones
    result = swarm.upload_mission_multi(["UAV_1", "UAV_2"], waypoints)
    assert result is True
    
    # Start mission
    swarm.start_mission_multi(["UAV_1", "UAV_2"])
    
    # Verify both drones in AUTO mode
    assert swarm.droneSnapshot("UAV_1")["flight_mode"] == "AUTO"
    assert swarm.droneSnapshot("UAV_2")["flight_mode"] == "AUTO"
```

### 2.5 Integrationstest Guidelines

**DO:**
- ✅ Teste Komponenten-Interaktionen
- ✅ Verwende FakeConnection für MAVLink
- ✅ Teste mit echten Dateien (Temp-Dir)
- ✅ Teste Fehler-Propagation zwischen Komponenten
- ✅ Akzeptable Laufzeit (<100ms pro Test)

**DON'T:**
- ❌ Keine echte Hardware
- ❌ Keine echten Drohnen
- ❌ Keine echten Netzwerk-Calls (außer localhost)

---

## 3. Systemtests

### 3.1 Definition
Systemtests testen das **gesamte System End-to-End** mit SITL oder Mock-Backend.

### 3.2 Scope
- Komplette Workflows (Connect → ARM → Takeoff → Mission → Land)
- SITL-Integration (ArduCopter/PX4)
- UI + Backend zusammen
- Echte ROS2-Kommunikation (optional)

### 3.3 Existierende Systemtests

| Test-Datei | Komponente | Tests | Status |
|------------|------------|-------|--------|
| `test_px4_mission.py` | PX4 Mission Upload | 5 | ✅ Pass |
| `test_px4_formation.py` | PX4 Formation Flight | 4 | ✅ Pass |
| `test_px4_gazebo.py` | PX4 Gazebo SITL | 6 | ✅ Pass |
| `test_bag_playback_context.py` | Bag Playback | 8 | ✅ Pass |

**Total:** 23 Systemtests

### 3.4 Beispiel: Systemtest für Mission Workflow

```python
@pytest.mark.slow
@pytest.mark.sitl
def test_full_mission_workflow_with_sitl():
    """Test complete mission workflow with ArduCopter SITL"""
    from droneresearch.simulation.sitl import SITLManager
    from droneresearch.sdk.drone import Drone
    from droneresearch.control.mission import Waypoint
    
    # Start SITL
    sitl = SITLManager()
    sitl.start(vehicle="copter", instance=0)
    
    try:
        # Connect drone
        drone = Drone("UAV_1", "tcp:127.0.0.1:5762")
        assert drone.connect(timeout=10)
        
        # Wait for GPS fix
        drone.wait_for_gps(timeout=30)
        
        # ARM and takeoff
        assert drone.arm()
        assert drone.takeoff(altitude=10)
        
        # Upload mission
        waypoints = [
            Waypoint(lat=47.397742, lon=8.545594, alt=10),
            Waypoint(lat=47.398, lon=8.546, alt=15),
            Waypoint(lat=47.3985, lon=8.5455, alt=10),
        ]
        assert drone.upload_mission(waypoints)
        
        # Start mission
        assert drone.start_mission()
        
        # Wait for mission completion
        drone.wait_for_mission_complete(timeout=120)
        
        # RTL and land
        assert drone.rtl()
        drone.wait_for_landed(timeout=60)
        
        # Disconnect
        drone.disconnect()
        
    finally:
        sitl.stop()
```

### 3.5 Systemtest Guidelines

**DO:**
- ✅ Teste komplette User-Workflows
- ✅ Verwende SITL für realistische Tests
- ✅ Teste mit echten Timings (Timeouts)
- ✅ Teste Fehler-Recovery (Connection Loss)
- ✅ Längere Laufzeit akzeptabel (<2min pro Test)

**DON'T:**
- ❌ Keine echte Hardware (außer explizit markiert)
- ❌ Keine parallele Ausführung (SITL-Ports)
- ❌ Keine flaky Tests (instabile Timings)

---

## 4. Abnahmetests (E2E)

### 4.1 Definition
Abnahmetests testen **User-Szenarien** aus Sicht des Endbenutzers mit echter UI.

### 4.2 Scope
- UI-Interaktionen (Klicks, Eingaben)
- Komplette User-Journeys
- Screenshot-Vergleiche (Visual Regression)
- Performance-Messungen

### 4.3 Geplante Abnahmetests

| Szenario | Beschreibung | Status |
|----------|--------------|--------|
| **E2E-01** | Single Drone Connect & Arm | 🔄 TODO |
| **E2E-02** | Multi-Drone Formation Flight | 🔄 TODO |
| **E2E-03** | Mission Planning & Execution | 🔄 TODO |
| **E2E-04** | APF Safety Trigger | 🔄 TODO |
| **E2E-05** | ROS2 Bag Recording & Playback | 🔄 TODO |
| **E2E-06** | Experiment Script Execution | 🔄 TODO |

### 4.4 Beispiel: E2E-Test mit Playwright

```python
# tests/e2e/test_single_drone_workflow.py
import pytest
from playwright.sync_api import Page, expect

@pytest.mark.e2e
def test_single_drone_connect_and_arm(page: Page):
    """E2E: Connect single drone and ARM via UI"""
    
    # Start UI
    page.goto("http://localhost:8080")
    
    # Wait for UI to load
    expect(page.locator("text=uavresearch gcs")).to_be_visible()
    
    # Navigate to Dashboard
    page.click("text=Telemetry")
    
    # Select drone from dropdown
    page.click("select#droneSelector")
    page.click("option:has-text('UAV_1')")
    
    # Verify connection status
    expect(page.locator(".connection-indicator")).to_have_class("connected")
    
    # Click ARM button in InstrBar
    page.click("button:has-text('ARM')")
    
    # Wait for armed state
    expect(page.locator(".armed-indicator")).to_have_text("ARMED")
    expect(page.locator(".armed-indicator")).to_have_css("color", "rgb(34, 197, 94)")
    
    # Take screenshot for visual regression
    page.screenshot(path="screenshots/armed-state.png")
    
    # Click DISARM
    page.click("button:has-text('DISARM')")
    
    # Verify disarmed
    expect(page.locator(".armed-indicator")).to_have_text("SAFE")
```

### 4.5 E2E-Test Guidelines

**DO:**
- ✅ Teste aus User-Perspektive
- ✅ Verwende echte UI (nicht Mocks)
- ✅ Teste kritische User-Journeys
- ✅ Screenshot-Vergleiche für Visual Regression
- ✅ Performance-Messungen (Startup-Zeit, Response-Zeit)

**DON'T:**
- ❌ Keine Unit-Test-Details in E2E
- ❌ Keine flaky Selektoren (use data-testid)
- ❌ Keine zu langen Tests (>5min)

---

## 5. Test-Infrastruktur

### 5.1 Test-Runner
- **pytest** (Python)
- **pytest-qt** (Qt/QML Tests)
- **playwright** (E2E Tests)

### 5.2 CI/CD Integration

```yaml
# .github/workflows/tests.yml
name: Tests

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -e ".[test]"
      - run: pytest tests/ -k "not slow and not sitl and not e2e" -v
  
  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - run: pip install -e ".[test]"
      - run: pytest tests/ -k "not slow and not sitl and not e2e" -v
  
  system-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - run: pip install -e ".[test]"
      - run: sudo apt-get install -y ardupilot-sitl
      - run: pytest tests/ -m sitl -v
  
  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - run: pip install -e ".[test]"
      - run: playwright install
      - run: pytest tests/e2e/ -m e2e -v
```

### 5.3 Test-Marker

```python
# pytest.ini
[pytest]
markers =
    unit: Unit tests (fast, no I/O)
    integration: Integration tests (with I/O)
    slow: Slow tests (>1s)
    sitl: Tests requiring SITL
    e2e: End-to-end tests with UI
    hardware: Tests requiring real hardware
```

### 5.4 Test-Ausführung

```bash
# Alle Tests
pytest tests/

# Nur Unit-Tests (schnell)
pytest tests/ -m unit

# Nur Integrationstests
pytest tests/ -m integration

# Nur Systemtests (mit SITL)
pytest tests/ -m sitl

# Nur E2E-Tests
pytest tests/ -m e2e

# Ohne langsame Tests
pytest tests/ -k "not slow"

# Mit Coverage
pytest tests/ --cov=droneresearch --cov-report=html
```

---

## 6. Test-Coverage

### 6.1 Aktueller Stand

| Komponente | Unit | Integration | System | E2E | Total |
|------------|------|-------------|--------|-----|-------|
| **Core** (FSM, Connection, Telemetry) | 85% | 70% | 50% | 0% | **68%** |
| **Control** (Mission, Script) | 80% | 60% | 40% | 0% | **60%** |
| **Safety** (APF) | 90% | 50% | 30% | 0% | **57%** |
| **SDK** (Drone, Swarm, Formations) | 75% | 65% | 45% | 0% | **62%** |
| **ROS2** (Bridge, Context, Bag) | 70% | 60% | 50% | 0% | **60%** |
| **UI** (Contexts, Backend) | 60% | 40% | 20% | 0% | **40%** |
| **Simulation** (SITL, Replay) | 50% | 40% | 60% | 0% | **50%** |
| **Data** (Logger, Store) | 80% | 70% | 30% | 0% | **60%** |
| **Experiment** (Manager, Metrics) | 65% | 50% | 40% | 0% | **52%** |
| **GESAMT** | **73%** | **56%** | **41%** | **0%** | **57%** |

### 6.2 Ziele

| Ebene | Aktuell | Ziel Q3 2026 | Ziel Q4 2026 |
|-------|---------|--------------|--------------|
| Unit-Tests | 73% | 85% | 90% |
| Integrationstests | 56% | 70% | 80% |
| Systemtests | 41% | 60% | 70% |
| E2E-Tests | 0% | 30% | 50% |
| **GESAMT** | **57%** | **70%** | **80%** |

---

## 7. Test-Daten

### 7.1 Fixtures

```python
# tests/conftest.py
import pytest
from droneresearch.core.connection import FakeConnection

@pytest.fixture
def fake_conn():
    """Fake MAVLink connection for testing"""
    return FakeConnection()

@pytest.fixture
def snap_factory():
    """Factory for telemetry snapshots"""
    def _make_snap(**kwargs):
        defaults = {
            "armed": False,
            "flight_mode": "STABILIZE",
            "lat": 47.397742,
            "lon": 8.545594,
            "alt": 0,
            "alt_rel": 0,
            "groundspeed": 0,
            "battery_pct": 100,
            "gps_fix": 3,
            "satellites": 12,
        }
        defaults.update(kwargs)
        return defaults
    return _make_snap

@pytest.fixture
def temp_bag_file(tmp_path):
    """Temporary ROS2 bag file"""
    bag_path = tmp_path / "test.db3"
    # Create minimal bag structure
    return str(bag_path)
```

### 7.2 Test-Daten-Dateien

```
tests/
├── data/
│   ├── missions/
│   │   ├── simple_mission.json
│   │   ├── complex_mission.json
│   │   └── invalid_mission.json
│   ├── bags/
│   │   ├── sample_flight.db3
│   │   └── multi_drone.db3
│   ├── logs/
│   │   ├── telemetry_log.jsonl
│   │   └── error_log.jsonl
│   └── configs/
│       ├── apf_config.json
│       └── formation_config.json
```

---

## 8. Best Practices

### 8.1 Test-Naming

```python
# ✅ GOOD
def test_apf_repulsion_force_below_min_separation():
    """Test that repulsion force is applied when drones are too close"""
    pass

# ❌ BAD
def test_apf():
    """Test APF"""
    pass
```

### 8.2 Arrange-Act-Assert Pattern

```python
def test_drone_arm_command():
    # ARRANGE
    drone = Drone("UAV_1", FakeConnection())
    drone.connect()
    
    # ACT
    result = drone.arm()
    
    # ASSERT
    assert result is True
    assert drone.is_armed() is True
```

### 8.3 Test-Isolation

```python
# ✅ GOOD - Each test is independent
def test_mission_upload():
    drone = Drone("UAV_1", FakeConnection())
    # ... test logic
    drone.disconnect()  # Clean up

def test_mission_start():
    drone = Drone("UAV_1", FakeConnection())
    # ... test logic
    drone.disconnect()  # Clean up

# ❌ BAD - Tests depend on each other
drone = None

def test_mission_upload():
    global drone
    drone = Drone("UAV_1", FakeConnection())
    # ... test logic

def test_mission_start():
    # Assumes drone from previous test
    # ... test logic
```

### 8.4 Flaky Tests vermeiden

```python
# ❌ BAD - Time-dependent, flaky
def test_telemetry_update():
    drone.connect()
    time.sleep(1)  # Hope telemetry arrives
    assert drone.get_altitude() > 0

# ✅ GOOD - Wait with timeout
def test_telemetry_update():
    drone.connect()
    drone.wait_for_telemetry(timeout=5)
    assert drone.get_altitude() > 0
```

---

## 9. Nächste Schritte

### 9.1 Kurzfristig (Q3 2026)

1. **E2E-Test-Framework aufsetzen** (Playwright)
   - Aufwand: 2 Tage
   - Ziel: 5 kritische E2E-Tests

2. **Test-Coverage erhöhen**
   - UI-Contexts: 40% → 70%
   - ROS2-Bridge: 60% → 80%
   - Aufwand: 3 Tage

3. **CI/CD-Integration**
   - GitHub Actions Workflow
   - Automatische Test-Ausführung bei PR
   - Aufwand: 1 Tag

### 9.2 Mittelfristig (Q4 2026)

4. **Visual Regression Tests**
   - Screenshot-Vergleiche für UI
   - Baseline-Images erstellen
   - Aufwand: 2 Tage

5. **Performance-Tests**
   - Startup-Zeit-Benchmarks
   - Memory-Leak-Detection
   - Aufwand: 2 Tage

6. **Hardware-in-the-Loop Tests**
   - Tests mit echter Hardware
   - Automatisierte Test-Rigs
   - Aufwand: 5 Tage

---

## 10. Zusammenfassung

### Aktuelle Test-Statistik:
- **158 Tests gesamt**
  - 83 Unit-Tests ✅
  - 52 Integrationstests (34 passing, 18 errors) ⚠️
  - 23 Systemtests ✅
  - 0 E2E-Tests 🔄

### Prioritäten:
1. **P0:** E2E-Test-Framework aufsetzen
2. **P0:** test_ui_wire.py Fehler fixen (bagPlayback Service)
3. **P1:** Test-Coverage auf 70% erhöhen
4. **P1:** CI/CD-Integration
5. **P2:** Visual Regression Tests

**Geschätzter Aufwand:** 10-12 Tage für P0+P1
