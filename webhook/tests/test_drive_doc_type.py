import pytest

from webhook_cursor_executor.drive_doc_type import (
    coerce_stored_drive_doc_type,
    normalize_drive_doc_type,
)


@pytest.mark.parametrize(
    ("event", "want"),
    [
        ({"file_type": "docx"}, "docx"),
        ({"file_type": "sheet"}, "sheet"),
        ({"file_type_v2": "DOCX"}, "docx"),
        ({}, "docx"),
        ({"file_type": "weird"}, "docx"),
    ],
)
def test_normalize_drive_doc_type(event, want):
    assert normalize_drive_doc_type(event, event_type="drive.file.edit_v1") == want


def test_coerce_stored_none_defaults_docx():
    assert coerce_stored_drive_doc_type(None) == "docx"


def test_coerce_stored_sheet_kept():
    assert coerce_stored_drive_doc_type("sheet") == "sheet"


def test_coerce_stored_invalid_defaults_docx():
    assert coerce_stored_drive_doc_type("nope") == "docx"
