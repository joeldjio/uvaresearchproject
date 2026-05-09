"""
Experiment: 10-Drohnen Kreis-Formation

- 10 SITL Instanzen (Mission Planner)
- Alle auf 20m abheben
- Kreis-Formation mit 8m Spacing
- 60 Sekunden halten
- Alle landen

Run:
    python experiments/swarm_10_circle.py
"""
import math
import threading
import time
from droneresearch import Swarm
from droneresearch.safety import APFSafetyFilter, APFFilterLoop, Pose3D

# ── Ports (Mission Planner 10-UAV SITL, SERIAL1) ─────────────────────────────
PORTS = {
    "UAV_1":  "tcp:127.0.0.1:5762",   # SERIAL1 of UAV sysid=1  (base 5760)
    "UAV_2":  "tcp:127.0.0.1:5772",   # SERIAL1 of UAV sysid=2  (base 5770)
    "UAV_3":  "tcp:127.0.0.1:5782",   # SERIAL1 of UAV sysid=3  (base 5780)
    "UAV_4":  "tcp:127.0.0.1:5792",   # SERIAL1 of UAV sysid=4  (base 5790)
    "UAV_5":  "tcp:127.0.0.1:5802",   # SERIAL1 of UAV sysid=5  (base 5800)
    "UAV_6":  "tcp:127.0.0.1:5812",   # SERIAL1 of UAV sysid=6  (base 5810)
    "UAV_7":  "tcp:127.0.0.1:5822",   # SERIAL1 of UAV sysid=7  (base 5820)
    "UAV_8":  "tcp:127.0.0.1:5832",   # SERIAL1 of UAV sysid=8  (base 5830)
    "UAV_9":  "tcp:127.0.0.1:5842",   # SERIAL1 of UAV sysid=9  (base 5840)
    "UAV_10": "tcp:127.0.0.1:5852",   # SERIAL1 of UAV sysid=10 (base 5850)
}

ALTITUDE   = 20.0   # Meter
HOLD_SECS  = 30.0   # Sekunden pro Formation
RADIUS_M   = 15.0   # Kreisradius in Metern
GRID_SPACE = 8.0    # Meter Abstand im Grid

# ── Kreis-Waypoints berechnen (relativ zu Home Canberra) ─────────────────────
HOME_LAT = -35.363352
HOME_LON =  149.165241

def offset_position(lat, lon, north_m, east_m):
    dlat = north_m / 111320.0
    dlon = east_m  / (111320.0 * math.cos(math.radians(lat)))
    return lat + dlat, lon + dlon

n = len(PORTS)

# ── Kreis-Positionen ──────────────────────────────────────────────────────────
circle_positions = []
circle_local = []
for i in range(n):
    angle = 2 * math.pi * i / n
    north = RADIUS_M * math.cos(angle)
    east  = RADIUS_M * math.sin(angle)
    lat, lon = offset_position(HOME_LAT, HOME_LON, north, east)
    circle_positions.append((lat, lon))
    circle_local.append(Pose3D(north, east, ALTITUDE))

# ── Grid-Positionen (4x3 minus 2 = 10 Drohnen) ───────────────────────────────
grid_positions = []
grid_local = []
cols = 4
for i in range(n):
    row = i // cols
    col = i % cols
    # Grid zentrieren: verschiebe um halbe Breite/Höhe
    north = (row - (math.ceil(n / cols) - 1) / 2.0) * GRID_SPACE
    east  = (col - (cols - 1) / 2.0) * GRID_SPACE
    lat, lon = offset_position(HOME_LAT, HOME_LON, north, east)
    grid_positions.append((lat, lon))
    grid_local.append(Pose3D(north, east, ALTITUDE))

# ── APF Safety Filter ─────────────────────────────────────────────────────────
# min_separation: Mindestabstand zwischen Drohnen
# Bei 10 Drohnen auf Radius 15m: Abstand je ~9.4m → 3m Minimum ist sicher
apf = APFSafetyFilter(
    min_separation  = 3.0,      # Mindestabstand in Metern
    max_speed       = 5.0,      # Max Schritt pro Update
    geofence_radius = RADIUS_M + 5.0,
    geofence_alt    = (1.0, ALTITUDE + 5.0),
    repulsion_gain  = 3.0,
    obstacle_radius = 5.0,      # Repulsion aktiviert < 5m
)

# Prüfe ob Zielpositionen sicher sind (kein Überlapp)
uav_names_list = list(PORTS.keys())
desired_poses  = {uav_names_list[i]: circle_local[i] for i in range(n)}

# Starte alle in Home-Position (alle auf 0,0) — APF schiebt sie auseinander
start_poses = {name: Pose3D(0, 0, ALTITUDE) for name in uav_names_list}

print("\n[APF] Prüfe Kollisionsfreiheit der Zielpositionen ...")
violations = apf.check_separation(desired_poses)
if violations:
    print(f"    WARNUNG: {len(violations)} Überlappungen in Zielpositionen!")
    for a, b, d in violations:
        print(f"    {a} ↔ {b}: {d:.2f}m (min={apf.min_separation}m)")
else:
    min_dist = min(
        circle_local[i].dist(circle_local[j])
        for i in range(n) for j in range(i+1, n)
    )
    print(f"    OK — Minimaler Abstand zwischen Zielpunkten: {min_dist:.1f}m")

# APF-Filter auf Startpositionen anwenden um sichere Wegpunkte zu berechnen
safe_poses = apf.filter(start_poses, desired_poses)
print(f"    APF-gefilterte Positionen berechnet.")

# ── Swarm aufbauen ────────────────────────────────────────────────────────────
swarm = Swarm()
for name, port in PORTS.items():
    swarm.add(name, port)

print("=" * 55)
print(f"  10-Drohnen Kreis-Experiment")
print(f"  Radius: {RADIUS_M}m | Höhe: {ALTITUDE}m | Hold: {HOLD_SECS}s")
print("=" * 55)

# ── Warten bis alle SITL-Instanzen hochgefahren sind ─────────────────────────
SITL_WARMUP = 15   # Sekunden warten nach Script-Start
print(f"\n[0] Warte {SITL_WARMUP}s auf SITL-Initialisierung (EKF/GPS) ...")
for i in range(SITL_WARMUP, 0, -1):
    print(f"    {i}s ...", end="\r")
    time.sleep(1.0)
print("    Bereit.                ")

# ── Verbinden ─────────────────────────────────────────────────────────────────
print("\n[1] Verbinde alle Drohnen ...")
results = swarm.connect_all(timeout=30.0)
connected = [k for k, v in results.items() if v]
failed    = [k for k, v in results.items() if not v]
print(f"    OK:     {connected}")
if failed:
    print(f"    FAILED: {failed}")

if not connected:
    raise SystemExit("Keine Drohne verbunden.")

if len(connected) < len(PORTS):
    print(f"\n    HINWEIS: Nur {len(connected)}/{len(PORTS)} Drohnen verbunden.")
    print("    Starte nur mit verbundenen Drohnen.")
    # Nicht verbundene aus dem Swarm entfernen
    for name in failed:
        swarm.remove(name)
    # circle_positions auf verbundene Drohnen anpassen
    connected_set = set(connected)
    drone_items_filtered = [(n, d) for n, d in swarm._drones.items() if n in connected_set]
else:
    drone_items_filtered = None   # alle verbunden

print(f"\n    {len(connected)}/{len(PORTS)} Drohnen verbunden.")

# ── Armen & Takeoff ───────────────────────────────────────────────────────────
print(f"\n[2] Armen ...")
swarm.arm_all()
time.sleep(2)

print(f"\n[3] Takeoff auf {ALTITUDE}m ...")
swarm.takeoff_all(altitude=ALTITUDE)
print("    Warte auf Takeoff ...")
time.sleep(8)

drone_items = drone_items_filtered if drone_items_filtered else list(swarm._drones.items())

def get_current_poses():
    poses = {}
    for name, drone in drone_items:
        try:
            dlat = (drone.lat - HOME_LAT) * 111320.0
            dlon = (drone.lon - HOME_LON) * 111320.0 * math.cos(math.radians(HOME_LAT))
            poses[name] = Pose3D(dlat, dlon, drone.altitude)
        except Exception:
            pass
    return poses

def on_violation(violations):
    for a, b, d in violations:
        print(f"  [APF WARNUNG] {a} ↔ {b}: {d:.2f}m < {apf.min_separation}m")

STAGGER_S = 2.0   # Sekunden Pause zwischen jedem Drohnen-Abflug

def _goto_nonblocking(drone, lat, lon, alt):
    """Setzt GUIDED-Mode und sendet goto ohne auf Ankunft zu warten."""
    try:
        drone.set_mode("GUIDED", timeout=3.0)
    except Exception:
        pass
    drone._conn.goto(lat, lon, alt)

def _dist_to(drone, lat, lon):
    """Horizontale Distanz in Metern zwischen Drohne und Ziel."""
    try:
        dlat = (drone.lat - lat) * 111320.0
        dlon = (drone.lon - lon) * 111320.0 * math.cos(math.radians(lat))
        return math.sqrt(dlat**2 + dlon**2)
    except Exception:
        return 9999.0

def fly_formation(label, positions, hold_secs):
    print(f"\n[Formation] {label} ...")
    active = list(drone_items)   # [(name, drone), ...]

    # Gestaffelter Abflug: alle 2s eine Drohne losschicken
    for i, (name, drone) in enumerate(active):
        lat, lon = positions[i]
        print(f"    {name:8s} → ({lat:.6f}, {lon:.6f})")
        _goto_nonblocking(drone, lat, lon, ALTITUDE)
        if i < len(active) - 1:
            time.sleep(STAGGER_S)

    # Warte bis alle < 3m vom Ziel (max 50s)
    print("    Warte auf Ankunft ...")
    deadline = time.time() + 50.0
    while time.time() < deadline:
        dists = [_dist_to(d, positions[i][0], positions[i][1])
                 for i, (_, d) in enumerate(active)]
        arrived = sum(1 for d in dists if d < 3.0)
        if arrived == len(active):
            break
        time.sleep(1.0)

    # APF-Check: Warne bei Kollisionen
    poses = get_current_poses()
    viols = apf.check_separation(poses) if poses else []
    if viols:
        for a, b, d in viols:
            print(f"  [APF WARNUNG] {a} ↔ {b}: {d:.2f}m")
    print(f"    In Position. Hovere {hold_secs}s ...")

    # Hold-Phase mit Status alle 10s
    apf_loop = APFFilterLoop(
        apf=apf, get_positions=get_current_poses,
        get_desired=lambda: desired_poses,
        on_safe=lambda _: None, on_violation=on_violation, hz=5.0,
    )
    apf_loop.start()
    start = time.time()
    last_tick = -1
    while time.time() - start < hold_secs:
        elapsed = time.time() - start
        tick = int(elapsed) // 10
        if tick != last_tick and elapsed > 0:
            last_tick = tick
            poses = get_current_poses()
            viols = apf.check_separation(poses) if poses else []
            status = f"[{len(viols)} Kollision(en)!]" if viols else "[OK]"
            print(f"\n    t={elapsed:.0f}s | APF {status}")
            for name, drone in active:
                try:
                    print(f"      {name:8s}: alt={drone.altitude:5.1f}m  bat={drone.battery:.0f}%")
                except Exception:
                    pass
        time.sleep(1.0)
    apf_loop.stop()

# ── Phase 1: Kreis ────────────────────────────────────────────────────────────
print(f"\n[4] Phase 1: Kreis-Formation (Radius={RADIUS_M}m, {HOLD_SECS}s)")
fly_formation(f"Kreis R={RADIUS_M}m", circle_positions, HOLD_SECS)

# ── Phase 2: Grid ─────────────────────────────────────────────────────────────
print(f"\n[5] Phase 2: Grid-Formation (4x3, Spacing={GRID_SPACE}m, {HOLD_SECS}s)")
desired_poses = {uav_names_list[i]: grid_local[i] for i in range(len(drone_items))}
fly_formation(f"Grid 4x3 spacing={GRID_SPACE}m", grid_positions, HOLD_SECS)

# ── Landen ────────────────────────────────────────────────────────────────────
print(f"\n[6] Alle landen ...")
swarm.land_all()
swarm.disconnect_all()

print("\n" + "=" * 55)
print("  Experiment abgeschlossen.")
print("  Logs: logs/  |  Plot: python tools/plot_flight.py")
print("=" * 55)
