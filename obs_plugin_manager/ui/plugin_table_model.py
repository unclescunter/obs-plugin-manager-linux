from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor

from ..models import PluginRow
from .icons import status_color, status_label

COLUMNS = ["Name", "Installed", "Latest", "Status", "Action"]
ACTION_COLUMN = 4


class PluginTableModel(QAbstractTableModel):
    def __init__(self, rows=None, parent=None):
        super().__init__(parent)
        self._rows = rows or []

    def set_rows(self, rows: list) -> None:
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def row_at(self, row_index: int) -> PluginRow:
        return self._rows[row_index]

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(COLUMNS)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return COLUMNS[section]
        return None

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0:
                return row.display_name
            if col == 1:
                return row.installed_version or "—"
            if col == 2:
                return row.latest_version or "—"
            if col == 3:
                return status_label(row.status)
            return None

        if role == Qt.ItemDataRole.ForegroundRole and col == 3:
            return QColor(status_color(row.status))

        return None
