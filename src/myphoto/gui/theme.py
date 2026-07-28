"""A modern dark theme (palette + QSS) for the desktop app's Qt Fusion style."""

from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

ACCENT = "#F2711C"
ACCENT_HOVER = "#FF8A3D"
ACCENT_PRESSED = "#D9600F"

_BG_WINDOW = "#1B1D22"
_BG_PANEL = "#22252B"
_BG_FIELD = "#2A2D34"
_BG_FIELD_HOVER = "#31343C"
_BORDER = "#3A3D45"
_TEXT = "#E8E9EC"
_TEXT_MUTED = "#9AA0A8"


def apply_dark_theme(app: QApplication) -> None:
    """Apply the Fusion style plus a dark palette and QSS to ``app``."""
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(_BG_WINDOW))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(_TEXT))
    palette.setColor(QPalette.ColorRole.Base, QColor(_BG_FIELD))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(_BG_PANEL))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(_BG_PANEL))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(_TEXT))
    palette.setColor(QPalette.ColorRole.Text, QColor(_TEXT))
    palette.setColor(QPalette.ColorRole.Button, QColor(_BG_FIELD))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(_TEXT))
    palette.setColor(QPalette.ColorRole.BrightText, QColor("#FF5C5C"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(ACCENT))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#1B1D22"))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(_TEXT_MUTED))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(_TEXT_MUTED))
    palette.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(_TEXT_MUTED)
    )
    app.setPalette(palette)

    app.setStyleSheet(_STYLESHEET)


_STYLESHEET = f"""
* {{
    font-family: "Segoe UI", "Inter", "Helvetica Neue", sans-serif;
    font-size: 13px;
    color: {_TEXT};
}}

QMainWindow, QWidget {{
    background-color: {_BG_WINDOW};
}}

QLabel#appTitle {{
    font-size: 18px;
    font-weight: 600;
    letter-spacing: 1px;
    color: {_TEXT};
    padding: 2px 0px;
}}

QLabel#appTitleAccent {{
    color: {ACCENT};
}}

QLabel#hintLabel {{
    color: {_TEXT_MUTED};
    font-size: 11px;
    padding-top: 2px;
}}

QSplitter::handle {{
    background-color: {_BORDER};
    width: 2px;
}}

QGroupBox {{
    background-color: {_BG_PANEL};
    border: 1px solid {_BORDER};
    border-radius: 8px;
    margin-top: 16px;
    padding: 14px 10px 10px 10px;
    font-weight: 600;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    top: 2px;
    padding: 0 6px;
    color: {ACCENT};
}}

QPushButton {{
    background-color: {_BG_FIELD};
    border: 1px solid {_BORDER};
    border-radius: 6px;
    padding: 7px 16px;
    font-weight: 500;
}}

QPushButton:hover {{
    background-color: {_BG_FIELD_HOVER};
    border-color: {ACCENT};
}}

QPushButton:pressed {{
    background-color: {_BORDER};
}}

QPushButton:disabled {{
    color: {_TEXT_MUTED};
    border-color: {_BORDER};
    background-color: {_BG_PANEL};
}}

QPushButton#primaryButton {{
    background-color: {ACCENT};
    border: 1px solid {ACCENT};
    color: #1B1D22;
    font-weight: 700;
}}

QPushButton#primaryButton:hover {{
    background-color: {ACCENT_HOVER};
    border-color: {ACCENT_HOVER};
}}

QPushButton#primaryButton:pressed {{
    background-color: {ACCENT_PRESSED};
}}

QPushButton#primaryButton:disabled {{
    background-color: {_BG_FIELD};
    border-color: {_BORDER};
    color: {_TEXT_MUTED};
}}

QLineEdit, QSpinBox, QComboBox {{
    background-color: {_BG_FIELD};
    border: 1px solid {_BORDER};
    border-radius: 6px;
    padding: 5px 8px;
    selection-background-color: {ACCENT};
}}

QLineEdit:hover, QSpinBox:hover, QComboBox:hover {{
    border-color: {ACCENT};
}}

QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
    border-color: {ACCENT};
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QComboBox QAbstractItemView {{
    background-color: {_BG_FIELD};
    border: 1px solid {_BORDER};
    selection-background-color: {ACCENT};
    selection-color: #1B1D22;
    outline: none;
}}

QSlider::groove:horizontal {{
    height: 4px;
    background: {_BORDER};
    border-radius: 2px;
}}

QSlider::sub-page:horizontal {{
    background: {ACCENT};
    border-radius: 2px;
}}

QSlider::handle:horizontal {{
    width: 16px;
    height: 16px;
    margin: -6px 0;
    background: {_TEXT};
    border-radius: 8px;
}}

QSlider::handle:horizontal:hover {{
    background: {ACCENT};
}}

QSlider::groove:horizontal:disabled {{
    background: {_BG_FIELD};
}}

QSlider::sub-page:horizontal:disabled {{
    background: {_BORDER};
}}

QSlider::handle:horizontal:disabled {{
    background: {_TEXT_MUTED};
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {_BORDER};
    border-radius: 4px;
    background: {_BG_FIELD};
}}

QCheckBox::indicator:hover {{
    border-color: {ACCENT};
}}

QCheckBox::indicator:checked {{
    background: {ACCENT};
    border-color: {ACCENT};
}}

QProgressBar {{
    background-color: {_BG_FIELD};
    border: 1px solid {_BORDER};
    border-radius: 6px;
    text-align: center;
    height: 18px;
}}

QProgressBar::chunk {{
    background-color: {ACCENT};
    border-radius: 5px;
}}

QScrollArea {{
    border: 1px solid {_BORDER};
    border-radius: 8px;
    background-color: {_BG_PANEL};
}}

QScrollBar:vertical, QScrollBar:horizontal {{
    background: transparent;
    border: none;
    margin: 0px;
}}

QScrollBar:vertical {{ width: 10px; }}
QScrollBar:horizontal {{ height: 10px; }}

QScrollBar::handle {{
    background: {_BORDER};
    border-radius: 5px;
    min-height: 24px;
    min-width: 24px;
}}

QScrollBar::handle:hover {{
    background: {ACCENT};
}}

QScrollBar::add-line, QScrollBar::sub-line {{
    height: 0px;
    width: 0px;
}}

QListWidget {{
    background-color: {_BG_PANEL};
    border: 1px solid {_BORDER};
    border-radius: 8px;
    padding: 4px;
}}

QListWidget::item {{
    padding: 6px;
    border-radius: 4px;
}}

QListWidget::item:selected {{
    background-color: {ACCENT};
    color: #1B1D22;
}}

QStatusBar {{
    background-color: {_BG_PANEL};
    color: {_TEXT_MUTED};
    border-top: 1px solid {_BORDER};
}}
"""
