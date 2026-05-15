pragma Singleton
import QtQuick

// ── Global UI state ───────────────────────────────────────────────────
// Replaces ad-hoc properties scattered across main.qml.
// Anyone can read/write the active selection via:
//   Cmp.AppState.selectedDroneId = "drone-1"
//
// Listening for changes:
//   Connections {
//       target: Cmp.AppState
//       function onSelectedDroneIdChanged() { … }
//   }
QtObject {
    id: state

    // ── Drone selection ───────────────────────────────────────────────
    property string selectedDroneId: ""

    // ── Map interaction modes ─────────────────────────────────────────
    property bool   mapPickMode:    false

    // ── Cached UI counts (driven by Python contexts) ──────────────────
    property int    droneCount:     0
    property int    connectedCount: 0

    // ── Multi-drone Mission Target Selection ──────────────────────────
    // Set of drone IDs that should receive the next "Start Mission" call.
    // Stored as a JS object {id: true} so QML can do O(1) lookups.
    // When the set is empty, callers fall back to ``selectedDroneId``.
    property var missionTargetIds:   ({})
    property int missionTargetCount: 0   // mirrors size of missionTargetIds

    signal missionTargetsChanged()

    function isMissionTarget(did) { return state.missionTargetIds[did] === true }

    function toggleMissionTarget(did) {
        var m = state.missionTargetIds
        if (m[did]) delete m[did]; else m[did] = true
        state.missionTargetIds = m
        var c = 0; for (var k in m) c++
        state.missionTargetCount = c
        state.missionTargetsChanged()
    }

    function clearMissionTargets() {
        state.missionTargetIds = ({})
        state.missionTargetCount = 0
        state.missionTargetsChanged()
    }

    function effectiveMissionTargets() {
        var ids = []
        for (var k in state.missionTargetIds) ids.push(k)
        if (ids.length === 0 && state.selectedDroneId) ids.push(state.selectedDroneId)
        return ids
    }

    // ── Helpers ───────────────────────────────────────────────────────
    function selectDrone(id) { selectedDroneId = id }
    function clearSelection() { selectedDroneId = "" }
    function hasSelection()   { return selectedDroneId !== "" }
}
