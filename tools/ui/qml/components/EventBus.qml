pragma Singleton
import QtQuick

// ── Event Bus ─────────────────────────────────────────────────────────
// Decoupled pub/sub for cross-component events that don't belong to a
// single Python context. Keeps panels from grabbing each other's IDs.
//
// Emit:
//   Cmp.EventBus.droneSelected("drone-1")
//   Cmp.EventBus.requestPanelOpen("dashboard")
//
// Listen:
//   Connections {
//       target: Cmp.EventBus
//       function onDroneSelected(id) { … }
//   }
//
// Why a Bus and not direct refs?
//   - Panels never know about each other.
//   - Adding a new event = adding one signal here, no plumbing.
QtObject {
    // ── Selection ─────────────────────────────────────────────────────
    signal droneSelected(string droneId)

    // ── Panel control (a panel can ask to be opened/closed) ───────────
    signal requestPanelOpen(string panelId)
    signal requestPanelClose(string panelId)

    // ── Map interaction ───────────────────────────────────────────────
    signal mapPickStarted(var target)         // panel asks to pick coords
    signal mapPickResolved(real lat, real lon)
    signal mapPickCancelled()

    // ── Generic toast / notification ──────────────────────────────────
    signal notify(string level, string text)  // level: info|warn|error|success
}
