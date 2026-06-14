#!/usr/bin/env python3
"""
Battery Monitor Demo - Zeigt verschiedene Konfigurationen

Dieses Beispiel demonstriert:
1. Standard-Konfiguration (20% Sicherheitsmarge)
2. Konservative Konfiguration (50% Sicherheitsmarge)
3. Aggressive Konfiguration (10% Sicherheitsmarge)
"""

from droneresearch.safety.battery_monitor import BatteryMonitor
import time


def demo_standard_config():
    """Standard-Konfiguration: 20% Sicherheitsmarge"""
    print("\n=== STANDARD KONFIGURATION ===")
    print("Sicherheitsmarge: 1.2 (20% Puffer)")
    print("Kritische Batterie: 20%")
    
    monitor = BatteryMonitor(
        critical_threshold=20.0,  # RTL bei 20% Batterie
        safety_margin=1.2,        # 20% Sicherheitspuffer
        min_samples_for_prediction=5
    )
    
    return monitor


def demo_conservative_config():
    """Konservative Konfiguration: 50% Sicherheitsmarge"""
    print("\n=== KONSERVATIVE KONFIGURATION ===")
    print("Sicherheitsmarge: 1.5 (50% Puffer)")
    print("Kritische Batterie: 25%")
    print("-> Fuer schwierige Bedingungen (Wind, Regen)")
    
    monitor = BatteryMonitor(
        critical_threshold=25.0,  # RTL bei 25% Batterie
        safety_margin=1.5,        # 50% Sicherheitspuffer
        min_samples_for_prediction=5
    )
    
    return monitor


def demo_aggressive_config():
    """Aggressive Konfiguration: 10% Sicherheitsmarge"""
    print("\n=== AGGRESSIVE KONFIGURATION ===")
    print("Sicherheitsmarge: 1.1 (10% Puffer)")
    print("Kritische Batterie: 15%")
    print("WARNUNG: Nur fuer ideale Bedingungen und erfahrene Piloten!")
    
    monitor = BatteryMonitor(
        critical_threshold=15.0,  # RTL bei 15% Batterie
        safety_margin=1.1,        # 10% Sicherheitspuffer
        min_samples_for_prediction=5
    )
    
    return monitor


def simulate_flight(monitor, config_name):
    """Simuliert einen Flug und zeigt RTL-Berechnungen"""
    print(f"\n--- Simulation: {config_name} ---")
    
    monitor.start_monitoring("UAV_1")
    home = (48.137, 11.575, 0.0)
    
    # Simuliere Flug: Drone fliegt 5km nach Norden
    positions = [
        (48.137, 11.575, 10.0),   # Start (Home)
        (48.147, 11.575, 10.0),   # 1km Nord
        (48.157, 11.575, 10.0),   # 2km Nord
        (48.167, 11.575, 10.0),   # 3km Nord
        (48.177, 11.575, 10.0),   # 4km Nord
        (48.187, 11.575, 10.0),   # 5km Nord
    ]
    
    battery_levels = [100.0, 85.0, 70.0, 55.0, 40.0, 25.0]
    
    for i, (pos, battery) in enumerate(zip(positions, battery_levels)):
        telemetry = {
            "battery_pct": battery,
            "lat": pos[0],
            "lon": pos[1],
            "alt_rel": pos[2]
        }
        monitor.update("UAV_1", telemetry)
        time.sleep(0.1)  # Simuliere Zeitverzögerung
        
        if i >= 4:  # Nach 4 Samples können wir RTL berechnen
            status = monitor.get_battery_status("UAV_1", home)
            if status:
                distance_km = (pos[0] - home[0]) * 111  # Grobe Umrechnung
                print(f"\nPosition: {distance_km:.1f}km von Home")
                print(f"  Batterie: {status.battery_pct:.1f}%")
                print(f"  RTL benötigt: {status.rtl_time_required:.0f}s")
                print(f"  RTL Batterie: {status.rtl_battery_required:.1f}%")
                
                if status.should_rtl:
                    print(f"  [!] RTL TRIGGER: {status.rtl_reason}")
                else:
                    print(f"  [OK] Batterie ausreichend")
    
    monitor.stop_monitoring("UAV_1")


def compare_configurations():
    """Vergleicht verschiedene Konfigurationen"""
    print("\n" + "="*60)
    print("VERGLEICH: Sicherheitsmarge-Einfluss")
    print("="*60)
    print("\nSzenario: Drone 5km von Home, 40% Batterie")
    print("RTL-Zeit (berechnet): 500 Sekunden")
    print("Stromverbrauch: 0.1% pro Sekunde")
    print()
    
    configs = [
        ("Aggressiv (1.1)", 1.1, 500 * 1.1, 500 * 1.1 * 0.1),
        ("Standard (1.2)", 1.2, 500 * 1.2, 500 * 1.2 * 0.1),
        ("Konservativ (1.5)", 1.5, 500 * 1.5, 500 * 1.5 * 0.1),
    ]
    
    print(f"{'Konfiguration':<20} {'RTL-Zeit':<15} {'Benötigte Batterie':<20} {'Trigger?'}")
    print("-" * 75)
    
    for name, margin, rtl_time, battery_needed in configs:
        trigger = "JA [!]" if battery_needed > 40 else "NEIN [OK]"
        print(f"{name:<20} {rtl_time:>6.0f}s {battery_needed:>10.1f}% {trigger:>15}")


def main():
    """Hauptprogramm"""
    print("="*60)
    print("BATTERY MONITOR - SICHERHEITSMARGE DEMO")
    print("="*60)
    
    # Zeige Konfigurationen
    monitor_std = demo_standard_config()
    monitor_cons = demo_conservative_config()
    monitor_aggr = demo_aggressive_config()
    
    # Vergleiche Konfigurationen
    compare_configurations()
    
    # Simuliere Flüge
    print("\n" + "="*60)
    print("FLIGHT SIMULATIONS")
    print("="*60)
    
    simulate_flight(monitor_std, "Standard (1.2)")
    simulate_flight(monitor_cons, "Konservativ (1.5)")
    simulate_flight(monitor_aggr, "Aggressiv (1.1)")
    
    # Empfehlungen
    print("\n" + "="*60)
    print("EMPFEHLUNGEN")
    print("="*60)
    print("""
    [IDEAL] Ideale Bedingungen (kein Wind, gutes Wetter):
        -> safety_margin = 1.1 - 1.2 (10-20% Puffer)
    
    [NORMAL] Normale Bedingungen (leichter Wind):
        -> safety_margin = 1.2 - 1.3 (20-30% Puffer)
    
    [SCHWIERIG] Schwierige Bedingungen (Wind, Regen):
        -> safety_margin = 1.5 - 2.0 (50-100% Puffer)
    
    [BERGIG] Bergiges Gelaende oder lange Distanzen:
        -> safety_margin = 1.5+ (50%+ Puffer)
    
    [WICHTIG]:
        - Hoehere Werte = Sicherer, aber kuerzere Missionen
        - Niedrigere Werte = Laengere Missionen, aber riskanter
        - Immer mit Testfluegen beginnen!
    """)


if __name__ == "__main__":
    main()

# Made with Bob
