import pytest

from webhook_cursor_executor.ingest_kind import derive_ingest_kind


def test_derive_ingest_kind_drive_file_prefix_requires_resolve_helper():
    with pytest.raises(ValueError, match="resolve_drive_file_ingest"):
        derive_ingest_kind({}, {"event_type": "drive.file.edit_v1"})


def test_derive_ingest_kind_cloud_docx_from_docx_prefix():
    assert derive_ingest_kind({}, {"event_type": "docx.document.updated_v1"}) == "cloud_docx"


def test_derive_ingest_kind_cloud_docx_when_wiki_in_event_type():
    assert (
        derive_ingest_kind({}, {"event_type": "drive.wiki.catalog.updated_v1"})
        == "cloud_docx"
    )


def test_derive_ingest_kind_prefers_header_event_type():
    assert (
        derive_ingest_kind(
            {"event_type": "drive.file.updated_v1"},
            {"event_type": "docx.document.updated_v1"},
        )
        == "cloud_docx"
    )


def test_derive_ingest_kind_unknown_raises():
    with pytest.raises(ValueError, match="unknown"):
        derive_ingest_kind({}, {"event_type": "sheet.record.changed_v1"})


def test_derive_ingest_kind_missing_event_type_raises():
    with pytest.raises(ValueError, match="missing"):
        derive_ingest_kind({}, {})
