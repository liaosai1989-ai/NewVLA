import pytest

from dify_upload import (
    DifyConfigError as ExportedDifyConfigError,
    DifyRequestError,
    DifyResponseError,
    DifyTargetConfig as ExportedDifyTargetConfig,
    DifyUploadError,
    UploadResult,
    resolve_dify_target,
    upload_csv_to_dify,
)
from dify_upload.config import DifyTargetConfig
from dify_upload.upload import DifyConfigError


def test_target_config_normalizes_api_base_and_rejects_invalid_fields():
    plain = DifyTargetConfig(
        api_base="https://dify.example.com",
        api_key="dataset-key",
        dataset_id="dataset-123",
    )
    spaced = DifyTargetConfig(
        api_base=" https://dify.example.com/v1/ ",
        api_key=" dataset-key ",
        dataset_id=" dataset-123 ",
    )
    with_v1 = DifyTargetConfig(
        api_base="https://dify.example.com/v1/",
        api_key="dataset-key",
        dataset_id="dataset-123",
        http_verify=False,
        timeout_seconds=12.5,
    )

    assert plain.api_base_v1 == "https://dify.example.com/v1"
    assert spaced.api_base_v1 == "https://dify.example.com/v1"
    assert with_v1.api_base_v1 == "https://dify.example.com/v1"
    assert spaced.api_key == "dataset-key"
    assert spaced.dataset_id == "dataset-123"
    assert plain.http_verify is True
    assert plain.timeout_seconds == 60.0
    assert with_v1.http_verify is False
    assert with_v1.timeout_seconds == 12.5

    with pytest.raises(DifyConfigError, match="api_base is empty"):
        DifyTargetConfig(
            api_base=" ",
            api_key="dataset-key",
            dataset_id="dataset-123",
        )

    with pytest.raises(DifyConfigError, match="api_key is empty"):
        DifyTargetConfig(
            api_base="https://dify.example.com",
            api_key=" ",
            dataset_id="dataset-123",
        )

    with pytest.raises(DifyConfigError, match="dataset_id is empty"):
        DifyTargetConfig(
            api_base="https://dify.example.com",
            api_key="dataset-key",
            dataset_id=" ",
        )

    with pytest.raises(DifyConfigError, match="timeout_seconds must be > 0"):
        DifyTargetConfig(
            api_base="https://dify.example.com",
            api_key="dataset-key",
            dataset_id="dataset-123",
            timeout_seconds=0,
        )


def test_package_root_exports_stable_public_api():
    assert ExportedDifyTargetConfig.__name__ == "DifyTargetConfig"
    assert UploadResult.__name__ == "UploadResult"
    assert resolve_dify_target.__name__ == "resolve_dify_target"
    assert upload_csv_to_dify.__name__ == "upload_csv_to_dify"
    assert issubclass(ExportedDifyConfigError, DifyUploadError)
    assert issubclass(DifyRequestError, DifyUploadError)
    assert issubclass(DifyResponseError, DifyUploadError)
