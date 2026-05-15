"""
Entry point: python -m tools.ui

Flags
-----
--legacy    Use old PyQt6 QWidget UI (main_window.py) instead of QML.
"""
import sys


def main():
    if "--legacy" in sys.argv:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QFont
        from tools.ui.main_window import MainWindow

        app = QApplication(sys.argv)
        app.setApplicationName("DroneResearch GCS")
        app.setApplicationVersion("0.2.0")
        app.setFont(QFont("Segoe UI", 10))
        win = MainWindow()
        win.show()
        sys.exit(app.exec())
    else:
        from tools.ui.app import run
        sys.exit(run())


if __name__ == "__main__":
    main()
