from PySide6.QtWidgets import QMessageBox

from ..models import CatalogEntry


def confirm_action(parent, entry: CatalogEntry, action_label: str, is_update: bool) -> bool:
    text = f"{action_label} “{entry.name}” version {entry.version}?"
    if is_update:
        text += (
            "\n\nThe existing installed folder will be backed up automatically "
            "before it's replaced."
        )
    reply = QMessageBox.question(
        parent,
        f"{action_label} plugin",
        text,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    return reply == QMessageBox.StandardButton.Yes
