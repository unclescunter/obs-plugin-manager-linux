import logging

from PySide6.QtCore import QThreadPool, QUrl
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtWidgets import (
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableView,
    QToolBar,
)

from .. import catalog as catalog_module
from .. import installer
from ..fs_scanner import scan_installed_plugins
from ..log_scanner import find_latest_log, load_log_text
from ..matcher import match
from ..rows import build_rows
from ..worker import Worker
from . import dialogs
from .plugin_table_model import ACTION_COLUMN, PluginTableModel

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OBS Plugin Manager")
        self.resize(960, 600)

        self.thread_pool = QThreadPool()
        self._all_rows = []
        self._visible_rows = []

        self._build_ui()
        self.refresh_all(force=False)

    def _build_ui(self) -> None:
        toolbar = QToolBar("Main")
        self.addToolBar(toolbar)

        refresh_action = QAction("Refresh Catalog", self)
        refresh_action.triggered.connect(lambda: self.refresh_all(force=True))
        toolbar.addAction(refresh_action)

        toolbar.addSeparator()

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search plugins...")
        self.search_edit.setMaximumWidth(260)
        self.search_edit.textChanged.connect(self._apply_filter)
        toolbar.addWidget(self.search_edit)

        self.model = PluginTableModel([])
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.doubleClicked.connect(self._open_forum_link)
        self.setCentralWidget(self.table)

        self.cache_label = QLabel("")
        self.statusBar().addPermanentWidget(self.cache_label)

    # -- data loading -----------------------------------------------------

    def refresh_all(self, force: bool = False) -> None:
        self.statusBar().showMessage("Refreshing catalog...")
        worker = Worker(self._load_data, force)
        worker.signals.finished.connect(self._on_data_loaded)
        worker.signals.error.connect(self._on_error)
        self.thread_pool.start(worker)

    @staticmethod
    def _load_data(force: bool) -> list:
        catalog = catalog_module.fetch_catalog(force=force)
        installed = scan_installed_plugins()
        match_results = match(installed, catalog)
        log_text = load_log_text(find_latest_log())
        return build_rows(match_results, catalog, log_text)

    def _on_data_loaded(self, rows: list) -> None:
        self._all_rows = rows
        self._apply_filter(self.search_edit.text())

        meta = catalog_module.cache_metadata()
        if meta and meta.get("fetched_at"):
            self.cache_label.setText(f"Catalog last updated: {meta['fetched_at']}")
        self.statusBar().showMessage("Ready", 3000)

    def _on_error(self, message: str) -> None:
        logger.error("Background job failed: %s", message)
        QMessageBox.warning(self, "Error", message.splitlines()[0])
        self.statusBar().showMessage("Error", 3000)

    # -- filtering / rendering ---------------------------------------------

    def _apply_filter(self, text: str) -> None:
        text = text.strip().lower()
        self._visible_rows = (
            self._all_rows
            if not text
            else [r for r in self._all_rows if text in r.display_name.lower()]
        )
        self.model.set_rows(self._visible_rows)
        self._add_action_buttons()

    def _add_action_buttons(self) -> None:
        for row_index, row in enumerate(self._visible_rows):
            widget = self._build_action_widget(row)
            index = self.model.index(row_index, ACTION_COLUMN)
            self.table.setIndexWidget(index, widget)

    def _build_action_widget(self, row):
        if row.catalog_entry is None or not row.catalog_entry.linux_download_url:
            return None

        if row.installed is None:
            button = QPushButton("Install")
            button.clicked.connect(lambda _checked=False, r=row: self._run_install(r, is_update=False))
            return button

        if row.status in ("update_available", "unknown"):
            button = QPushButton("Update")
            button.clicked.connect(lambda _checked=False, r=row: self._run_install(r, is_update=True))
            return button

        return None

    def _open_forum_link(self, index) -> None:
        row = self._visible_rows[index.row()]
        if row.forum_url:
            QDesktopServices.openUrl(QUrl(row.forum_url))

    # -- install / update ---------------------------------------------------

    def _run_install(self, row, is_update: bool) -> None:
        entry = row.catalog_entry
        action_label = "Update" if is_update else "Install"
        if not dialogs.confirm_action(self, entry, action_label, is_update):
            return

        self.statusBar().showMessage(f"{action_label}ing {entry.name}...")
        worker = Worker(installer.install_or_update, entry, row.installed)
        worker.kwargs["progress_cb"] = lambda msg: worker.signals.progress.emit(msg)
        worker.signals.progress.connect(lambda msg: self.statusBar().showMessage(msg))
        worker.signals.finished.connect(lambda record: self._on_install_finished(record, action_label))
        worker.signals.error.connect(self._on_error)
        self.thread_pool.start(worker)

    def _on_install_finished(self, record, action_label: str) -> None:
        self.statusBar().showMessage(
            f"{record.catalog_name} {record.installed_version} installed.", 5000
        )
        self.refresh_all(force=False)
