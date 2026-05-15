pragma Singleton
import QtQuick

// ── Centralised design tokens ─────────────────────────────────────────
// Single source of truth for colours, typography and spacing.
// Use:   Theme.bg, Theme.accent, Theme.fontMono, Theme.spacing(2), …
//
// Registered as a QML Singleton via qmldir. Once we have the module set
// up, `import "components" as Cmp` makes `Cmp.Theme.bg` available.
QtObject {
    // ── Surface colours ───────────────────────────────────────────────
    readonly property color bg:           "#0f1117"
    readonly property color bgElevated:   "#1a2035"
    readonly property color bgInput:      "#1e2535"
    readonly property color bgPanel:      "#161b27"

    // ── Borders / outlines ────────────────────────────────────────────
    readonly property color border:       "#2d3748"
    readonly property color borderMuted:  "#1e293b"
    readonly property color borderStrong: "#334155"

    // ── Text ──────────────────────────────────────────────────────────
    readonly property color textPrimary:   "#e2e8f0"
    readonly property color textSecondary: "#94a3b8"
    readonly property color textMuted:     "#64748b"
    readonly property color textFaded:     "#475569"

    // ── Brand / accents ───────────────────────────────────────────────
    readonly property color accent:       "#2563eb"   // primary blue
    readonly property color accentLight:  "#93c5fd"
    readonly property color success:      "#22c55e"
    readonly property color warning:      "#f59e0b"
    readonly property color danger:       "#ef4444"
    readonly property color info:         "#06b6d4"
    readonly property color violet:       "#8b5cf6"

    // ── Drone type colours (consistent across UI) ─────────────────────
    readonly property color droneGeneric:     "#2563eb"
    readonly property color droneObservation: "#8b5cf6"

    function droneColor(type) {
        return type === "observation" ? droneObservation : droneGeneric
    }

    // ── Typography ────────────────────────────────────────────────────
    readonly property string fontSans: "Segoe UI"
    readonly property string fontMono: "Consolas"

    readonly property int   fontXS: 8
    readonly property int   fontS:  10
    readonly property int   fontM:  11
    readonly property int   fontL:  13
    readonly property int   fontXL: 16

    // ── Spacing scale (4px grid) ──────────────────────────────────────
    function spacing(n) { return n * 4 }

    readonly property int radiusS: 4
    readonly property int radiusM: 6
    readonly property int radiusL: 8
}
