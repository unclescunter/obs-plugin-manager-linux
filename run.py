#!/usr/bin/env python3
import logging
import sys

from PySide6.QtWidgets import QApplication

from obs_plugin_manager.ui.main_window import MainWindow


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    app = QApplication(sys.argv)
    app.setApplicationName("OBS Plugin Manager")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
