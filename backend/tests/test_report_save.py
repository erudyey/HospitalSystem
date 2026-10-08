"""Native CSV save contracts using disposable files and a mocked dialog."""

from unittest.mock import Mock, patch

import pytest

from desktop.reports import save_report_csv

FILENAME = "daily-report-2026-09-01-demo-clinic.csv"
CONTENT = "\ufeffdoctor_name,appointments\r\nDoctor One,1\r\n"


def test_native_save_preserves_utf8_bom_and_uses_csv_dialog(tmp_path):
    destination = tmp_path / "report.csv"
    window = Mock()
    window.create_file_dialog.return_value = (str(destination),)
    assert save_report_csv(window, FILENAME, CONTENT) == {"status": "saved"}
    assert destination.read_bytes() == CONTENT.encode("utf-8")
    assert window.create_file_dialog.call_args.kwargs["file_types"] == ("CSV files (*.csv)",)


def test_cancelled_native_dialog_writes_nothing(tmp_path):
    window = Mock()
    window.create_file_dialog.return_value = None
    assert save_report_csv(window, FILENAME, CONTENT) == {"status": "cancelled"}
    assert list(tmp_path.iterdir()) == []


def test_failed_save_preserves_existing_file_and_removes_temporary_file(tmp_path):
    destination = tmp_path / "report.csv"
    destination.write_bytes(b"original")
    window = Mock()
    window.create_file_dialog.return_value = (str(destination),)
    with (
        patch("desktop.reports.os.replace", side_effect=PermissionError("Synthetic write failure")),
        pytest.raises(PermissionError),
    ):
        save_report_csv(window, FILENAME, CONTENT)
    assert destination.read_bytes() == b"original"
    assert list(tmp_path.iterdir()) == [destination]


def test_native_save_refuses_non_csv_destinations_and_unsafe_suggestions(tmp_path):
    window = Mock()
    destination = tmp_path / "clinic.sqlite3"
    window.create_file_dialog.return_value = (str(destination),)
    with pytest.raises(ValueError, match="ending in .csv"):
        save_report_csv(window, FILENAME, CONTENT)
    assert not destination.exists()
    with pytest.raises(ValueError, match="filename"):
        save_report_csv(window, "../report.csv", CONTENT)
