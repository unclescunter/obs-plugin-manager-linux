"""Small colored status dots, used instead of theme-dependent icon packs so
status is legible under any Qt style/theme."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap

STATUS_COLORS = {
    "up_to_date": "#2e7d32",
    "update_available": "#f9a825",
    "not_installed": "#757575",
    "installed_unmanaged": "#5c6bc0",
    "not_available_linux": "#9e9e9e",
    "unknown": "#9e9e9e",
}

STATUS_LABELS = {
    "up_to_date": "Up to date",
    "update_available": "Update available",
    "not_installed": "Not installed",
    "installed_unmanaged": "Installed (unmanaged)",
    "not_available_linux": "Not available for Linux",
    "unknown": "Unknown",
}


def status_label(status: str) -> str:
    return STATUS_LABELS.get(status, status)


def status_color(status: str) -> str:
    return STATUS_COLORS.get(status, "#000000")


def status_icon(status: str, size: int = 12) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor(status_color(status)))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(0, 0, size, size)
    painter.end()
    return QIcon(pixmap)
