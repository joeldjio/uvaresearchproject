"""
Dark modern Qt6 stylesheet for the DroneResearch GCS.

Usage
-----
from tools.ui.style import Colors, DARK_THEME, TAB_STYLESHEET, STATE_COLORS, DRONE_COLORS
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class _Colors:
    """Single source of truth for all UI colour values."""
    # Backgrounds
    bg_app:      str = "#0f1117"
    bg_panel:    str = "#161b27"
    bg_card:     str = "#1a2035"
    bg_input:    str = "#1e2535"
    bg_hover:    str = "#263148"
    bg_console:  str = "#0d1117"
    # Borders
    border:      str = "#2d3748"
    # Accent
    blue:        str = "#2563eb"
    blue_dark:   str = "#1d4ed8"
    blue_dim:    str = "#4a6fa5"
    # Semantic
    green:       str = "#22c55e"
    green_dark:  str = "#15803d"
    yellow:      str = "#f59e0b"
    yellow_dark: str = "#b45309"
    orange:      str = "#f97316"
    red:         str = "#dc2626"
    red_dark:    str = "#b91c1c"
    purple:      str = "#8b5cf6"
    teal:        str = "#14b8a6"
    cyan:        str = "#06b6d4"
    lime:        str = "#84cc16"
    pink:        str = "#ec4899"
    # Text
    text_primary:  str = "#e2e8f0"
    text_muted:    str = "#94a3b8"
    text_disabled: str = "#4a5568"
    text_dim:      str = "#64748b"
    # Sky / Ground (attitude indicator)
    sky:   str = "#1e40af"
    earth: str = "#78350f"


Colors = _Colors()


TAB_STYLESHEET = f"""
    QTabWidget::pane {{ border: none; background: {Colors.bg_app}; }}
    QTabBar::tab {{
        background: {Colors.bg_panel};
        color: {Colors.text_dim};
        padding: 12px 22px;
        font-weight: 500;
        font-size: 13px;
        border: none;
        border-bottom: 2px solid transparent;
        margin-right: 1px;
    }}
    QTabBar::tab:selected {{
        color: {Colors.text_primary};
        border-bottom: 2px solid {Colors.blue};
        background: {Colors.bg_app};
    }}
    QTabBar::tab:hover:!selected {{
        color: {Colors.text_muted};
        background: {Colors.bg_card};
    }}
"""

STATUSBAR_STYLESHEET = f"""
    QStatusBar {{
        background: {Colors.bg_panel};
        color: {Colors.text_dim};
        border-top: 1px solid {Colors.border};
        font-size: 11px;
    }}
"""

DARK_THEME = """
QMainWindow, QDialog, QWidget {
    background-color: #0f1117;
    color: #e2e8f0;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}

/* ── Tabs ── */
QTabWidget::pane {
    border: 1px solid #2d3748;
    background-color: #161b27;
    border-radius: 8px;
}
QTabBar::tab {
    background: #1e2535;
    color: #94a3b8;
    padding: 10px 22px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    margin-right: 2px;
    font-weight: 500;
}
QTabBar::tab:selected {
    background: #2563eb;
    color: #ffffff;
}
QTabBar::tab:hover:!selected {
    background: #263148;
    color: #e2e8f0;
}

/* ── GroupBox ── */
QGroupBox {
    border: 1px solid #2d3748;
    border-radius: 10px;
    margin-top: 14px;
    padding: 10px 8px 8px 8px;
    font-weight: 600;
    color: #94a3b8;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}

/* ── Buttons ── */
QPushButton {
    background-color: #1e2535;
    color: #e2e8f0;
    border: 1px solid #2d3748;
    border-radius: 8px;
    padding: 8px 18px;
    font-weight: 500;
    min-height: 34px;
}
QPushButton:hover {
    background-color: #263148;
    border-color: #4a6fa5;
}
QPushButton:pressed {
    background-color: #1a4080;
}
QPushButton:disabled {
    color: #4a5568;
    border-color: #1e2535;
    background-color: #161b27;
}

QPushButton#btn_primary {
    background-color: #2563eb;
    border-color: #2563eb;
    color: white;
    font-weight: 600;
}
QPushButton#btn_primary:hover {
    background-color: #1d4ed8;
}
QPushButton#btn_danger {
    background-color: #dc2626;
    border-color: #dc2626;
    color: white;
    font-weight: 600;
}
QPushButton#btn_danger:hover {
    background-color: #b91c1c;
}
QPushButton#btn_success {
    background-color: #16a34a;
    border-color: #16a34a;
    color: white;
    font-weight: 600;
}
QPushButton#btn_success:hover {
    background-color: #15803d;
}
QPushButton#btn_warning {
    background-color: #d97706;
    border-color: #d97706;
    color: white;
    font-weight: 600;
}
QPushButton#btn_warning:hover {
    background-color: #b45309;
}

/* ── Table ── */
QTableWidget {
    background-color: #161b27;
    alternate-background-color: #1a2035;
    border: 1px solid #2d3748;
    border-radius: 8px;
    gridline-color: #2d3748;
    selection-background-color: #2563eb;
    selection-color: white;
}
QTableWidget::item {
    padding: 6px 10px;
    border: none;
}
QHeaderView::section {
    background-color: #1e2535;
    color: #94a3b8;
    padding: 8px 10px;
    border: none;
    border-bottom: 2px solid #2563eb;
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* ── Input / Combo / Spin ── */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #1e2535;
    color: #e2e8f0;
    border: 1px solid #2d3748;
    border-radius: 6px;
    padding: 6px 10px;
    min-height: 28px;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border-color: #2563eb;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    background-color: #1e2535;
    border: 1px solid #2d3748;
    selection-background-color: #2563eb;
}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
    background-color: #263148;
    border: none;
    width: 18px;
}

/* ── ScrollBar ── */
QScrollBar:vertical {
    background: #161b27;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #2d3748;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #4a6fa5;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QScrollBar:horizontal {
    background: #161b27;
    height: 8px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal {
    background: #2d3748;
    border-radius: 4px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover { background: #4a6fa5; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* ── TextEdit (log) ── */
QTextEdit, QPlainTextEdit {
    background-color: #0d1117;
    color: #8be9fd;
    border: 1px solid #2d3748;
    border-radius: 8px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
    padding: 6px;
}

/* ── Slider ── */
QSlider::groove:horizontal {
    height: 4px;
    background: #2d3748;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #2563eb;
    width: 14px;
    height: 14px;
    border-radius: 7px;
    margin: -5px 0;
}
QSlider::sub-page:horizontal {
    background: #2563eb;
    border-radius: 2px;
}

/* ── Label ── */
QLabel#label_title {
    font-size: 22px;
    font-weight: 700;
    color: #e2e8f0;
    letter-spacing: 1px;
}
QLabel#label_subtitle {
    font-size: 12px;
    color: #64748b;
}
QLabel#status_ok   { color: #22c55e; font-weight: 600; }
QLabel#status_warn { color: #f59e0b; font-weight: 600; }
QLabel#status_err  { color: #ef4444; font-weight: 600; }

/* ── Separator ── */
QFrame[frameShape="4"], QFrame[frameShape="5"] {
    color: #2d3748;
}

/* ── Tooltip ── */
QToolTip {
    background-color: #1e2535;
    color: #e2e8f0;
    border: 1px solid #2563eb;
    border-radius: 4px;
    padding: 4px 8px;
}

/* ── Progress ── */
QProgressBar {
    background-color: #1e2535;
    border: 1px solid #2d3748;
    border-radius: 6px;
    text-align: center;
    color: white;
    font-weight: 600;
    height: 18px;
}
QProgressBar::chunk {
    background-color: #2563eb;
    border-radius: 5px;
}
"""

# Status badge colors
STATE_COLORS = {
    "IDLE":      "#64748b",
    "ARMING":    "#f59e0b",
    "ARMED":     "#f97316",
    "TAKEOFF":   "#3b82f6",
    "FLYING":    "#22c55e",
    "MISSION":   "#8b5cf6",
    "LANDING":   "#f59e0b",
    "RTL":       "#f97316",
    "EMERGENCY": "#ef4444",
    "UNKNOWN":   "#374151",
}

DRONE_COLORS = ["#3b82f6", "#22c55e", "#f59e0b", "#ec4899",
                "#8b5cf6", "#14b8a6", "#f97316", "#06b6d4",
                "#84cc16", "#a855f7"]
