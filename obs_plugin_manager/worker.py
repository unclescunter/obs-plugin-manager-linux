"""Generic background-job runner so network/extraction work never blocks the
Qt UI thread.
"""

import traceback
from typing import Callable

from PySide6.QtCore import QObject, QRunnable, Signal


class WorkerSignals(QObject):
    progress = Signal(str)
    finished = Signal(object)
    error = Signal(str)


class Worker(QRunnable):
    def __init__(self, fn: Callable, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    def run(self) -> None:
        try:
            result = self.fn(*self.args, **self.kwargs)
        except Exception as exc:  # noqa: BLE001 - surfaced to the UI, not swallowed
            self.signals.error.emit(f"{exc}\n{traceback.format_exc()}")
        else:
            self.signals.finished.emit(result)
