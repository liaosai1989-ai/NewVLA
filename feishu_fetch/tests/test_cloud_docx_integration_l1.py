import os

import pytest

pytestmark = pytest.mark.l1_cloud


@pytest.mark.l1_cloud
def test_cloud_docx_authorized_real() -> None:
    if not os.environ.get("FEISHU_FETCH_L1_RUN"):
        pytest.skip("set FEISHU_FETCH_L1_RUN=1 and configure doc tokens")
    # 在实现真断言之前保留下一行，避免受控机只开 RUN 即因 assert False 红；落地后删 skip 并写真实 document_id
    pytest.skip("L1 授权路径尚未接真云，删除本行后补全")
    # 使用真实 document_id，断言 fetch 成功


@pytest.mark.l1_cloud
def test_cloud_docx_unauthorized_real() -> None:
    if not os.environ.get("FEISHU_FETCH_L1_RUN"):
        pytest.skip("set FEISHU_FETCH_L1_RUN=1 and configure doc tokens")
    pytest.skip("L1 未授权路径尚未接真云，删除本行后补全")
    # 未授权文档，断言 permission 类错误
