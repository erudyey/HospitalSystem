"""Save report CSV files through a native, user-controlled destination dialog."""

import os
import re
import tempfile
from pathlib import Path
from typing import Any


def save_report_csv(window: Any, filename: str, content: str) -> dict[str, str]:
    """Write the CSV atomically; cancellation never creates a file."""
    if not isinstance(filename, str) or not re.fullmatch(
        r"daily-report-\d{4}-\d{2}-\d{2}-(clinic|demo)-(clinic|doctor)\.csv", filename
    ):
        raise ValueError("Invalid report filename.")
    if not isinstance(content, str):
        raise ValueError("CSV content must be text.")
    from webview import FileDialog

    paths = window.create_file_dialog(
        FileDialog.SAVE, save_filename=filename, file_types=("CSV files (*.csv)",)
    )
    if not paths:
        return {"status": "cancelled"}
    destination = Path(paths[0])
    if destination.suffix.lower() != ".csv":
        raise ValueError("Choose a destination ending in .csv.")
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            prefix=".daily-report-",
            suffix=".tmp",
            dir=destination.parent,
            delete=False,
        ) as output:
            temporary = Path(output.name)
            output.write(content)
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {"status": "saved"}
