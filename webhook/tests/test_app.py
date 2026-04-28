from fakeredis import FakeStrictRedis
from fastapi.testclient import TestClient

from webhook_cursor_executor.app import build_app, create_app
from webhook_cursor_executor.settings import (
    ExecutorSettings,
    FolderRoute,
    PipelineWorkspace,
    RoutingConfig,
)
from webhook_cursor_executor.state_store import RedisStateStore


class FakeQueue:
    def __init__(self) -> None:
        self.calls = []

    def enqueue(self, job_name: str, **kwargs) -> None:
        self.calls.append((job_name, kwargs))

def test_health_endpoint_returns_ok_no_redis():
    settings = ExecutorSettings(
        feishu_encrypt_key="",
        feishu_verification_token="",
    )
    routing = RoutingConfig(
        pipeline_workspace=PipelineWorkspace(
            path="C:\\workspaces\\pipeline",
            cursor_timeout_seconds=7200,
        ),
        folder_routes=[
            FolderRoute(
                folder_token="fld_team_a",
                qa_rule_file="rules/team_a_qa.md",
                dataset_id="dataset_team_a",
            )
        ],
    )
    queue = FakeQueue()
    store = RedisStateStore(redis_client=FakeStrictRedis(decode_responses=True))
    app = create_app(
        settings=settings,
        routing_config=routing,
        state_store=store,
        queue=queue,
    )
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_default_webhook_path_is_stable():
    settings = ExecutorSettings()

    assert settings.feishu_webhook_path == "/webhook/feishu"


def test_webhook_uses_redis_event_seen_and_enqueues_schedule():
    settings = ExecutorSettings(
        feishu_encrypt_key="",
        feishu_verification_token="",
    )
    routing = RoutingConfig(
        pipeline_workspace=PipelineWorkspace(
            path="C:\\workspaces\\pipeline",
            cursor_timeout_seconds=7200,
        ),
        folder_routes=[
            FolderRoute(
                folder_token="fld_team_a",
                qa_rule_file="rules/team_a_qa.md",
                dataset_id="dataset_team_a",
            )
        ],
    )
    queue = FakeQueue()
    store = RedisStateStore(redis_client=FakeStrictRedis(decode_responses=True))
    app = create_app(
        settings=settings,
        routing_config=routing,
        state_store=store,
        queue=queue,
    )
    client = TestClient(app)

    payload = {
        "header": {"event_id": "evt_1", "event_type": "drive.file.updated_v1"},
        "event": {"document_id": "doc_1", "folder_token": "fld_team_a"},
    }

    first = client.post("/webhook/feishu", json=payload)
    second = client.post("/webhook/feishu", json=payload)

    assert first.status_code == 200
    assert second.json()["msg"] == "duplicate"
    assert queue.calls[0][0] == "schedule_document_job"
    sn = store.load_snapshot("doc_1")
    assert sn is not None
    assert sn.ingest_kind == "drive_file"
    assert sn.dify_target_key == "DEFAULT"


def test_drive_edit_without_folder_token_enqueues_ingest_not_listing_in_http():
    settings = ExecutorSettings(
        feishu_encrypt_key="",
        feishu_verification_token="",
        feishu_app_id="cli_x",
        feishu_app_secret="sec",
    )
    routing = RoutingConfig(
        pipeline_workspace=PipelineWorkspace(
            path="C:\\workspaces\\pipeline",
            cursor_timeout_seconds=7200,
        ),
        folder_routes=[
            FolderRoute(
                folder_token="fld_team_a",
                qa_rule_file="rules/team_a_qa.md",
                dataset_id="dataset_team_a",
            )
        ],
    )
    queue = FakeQueue()
    store = RedisStateStore(redis_client=FakeStrictRedis(decode_responses=True))
    app = create_app(
        settings=settings,
        routing_config=routing,
        state_store=store,
        queue=queue,
    )
    client = TestClient(app)

    payload = {
        "header": {"event_id": "evt_edit", "event_type": "drive.file.edit_v1"},
        "event": {"file_token": "docx_token_1", "file_type": "docx"},
    }
    r = client.post("/webhook/feishu", json=payload)
    assert r.status_code == 200
    assert r.json().get("msg") == "ok"
    assert queue.calls[0][0] == "ingest_feishu_document_event"
    assert queue.calls[0][1]["document_id"] == "docx_token_1"
    assert queue.calls[0][1]["ingest_kind"] == "drive_file"
    assert not list(store.redis.scan_iter("webhook:event_seen:*"))


def test_drive_edit_without_folder_token_and_without_app_creds_returns_400():
    settings = ExecutorSettings(
        feishu_encrypt_key="",
        feishu_verification_token="",
        feishu_app_id="",
        feishu_app_secret="",
    )
    routing = RoutingConfig(
        pipeline_workspace=PipelineWorkspace(
            path="C:\\workspaces\\pipeline",
            cursor_timeout_seconds=7200,
        ),
        folder_routes=[
            FolderRoute(
                folder_token="fld_team_a",
                qa_rule_file="rules/team_a_qa.md",
                dataset_id="dataset_team_a",
            )
        ],
    )
    queue = FakeQueue()
    store = RedisStateStore(redis_client=FakeStrictRedis(decode_responses=True))
    app = create_app(
        settings=settings,
        routing_config=routing,
        state_store=store,
        queue=queue,
    )
    client = TestClient(app)
    r = client.post(
        "/webhook/feishu",
        json={
            "header": {"event_id": "e1", "event_type": "drive.file.edit_v1"},
            "event": {"file_token": "ft1"},
        },
    )
    assert r.status_code == 400
    assert "folder_token" in (r.json().get("error") or "")
    assert queue.calls == []


def test_folder_route_fail_does_not_mark_event_seen():
    settings = ExecutorSettings(
        feishu_encrypt_key="",
        feishu_verification_token="",
    )
    routing = RoutingConfig(
        pipeline_workspace=PipelineWorkspace(
            path="C:\\workspaces\\pipeline",
            cursor_timeout_seconds=7200,
        ),
        folder_routes=[
            FolderRoute(
                folder_token="fld_team_a",
                qa_rule_file="rules/team_a_qa.md",
                dataset_id="dataset_team_a",
            )
        ],
    )
    queue = FakeQueue()
    store = RedisStateStore(redis_client=FakeStrictRedis(decode_responses=True))
    app = create_app(
        settings=settings,
        routing_config=routing,
        state_store=store,
        queue=queue,
    )
    client = TestClient(app)

    bad = client.post(
        "/webhook/feishu",
        json={
            "header": {"event_id": "evt_recover", "event_type": "x"},
            "event": {"document_id": "d1", "folder_token": "totally_unknown"},
        },
    )
    assert bad.status_code == 400
    assert not list(store.redis.scan_iter("webhook:event_seen:*"))

    good = client.post(
        "/webhook/feishu",
        json={
            "header": {
                "event_id": "evt_recover",
                "event_type": "drive.file.updated_v1",
            },
            "event": {"document_id": "d1", "folder_token": "fld_team_a"},
        },
    )
    assert good.status_code == 200
    assert good.json().get("msg") == "ok"


def test_webhook_rejects_unknown_event_type_for_ingest_kind():
    settings = ExecutorSettings(
        feishu_encrypt_key="",
        feishu_verification_token="",
    )
    routing = RoutingConfig(
        pipeline_workspace=PipelineWorkspace(
            path="C:\\workspaces\\pipeline",
            cursor_timeout_seconds=7200,
        ),
        folder_routes=[
            FolderRoute(
                folder_token="fld_team_a",
                qa_rule_file="rules/team_a_qa.md",
                dataset_id="dataset_team_a",
            )
        ],
    )
    queue = FakeQueue()
    store = RedisStateStore(redis_client=FakeStrictRedis(decode_responses=True))
    app = create_app(
        settings=settings,
        routing_config=routing,
        state_store=store,
        queue=queue,
    )
    client = TestClient(app)
    r = client.post(
        "/webhook/feishu",
        json={
            "header": {"event_id": "e_bad_ingest", "event_type": "sheet.foo_v1"},
            "event": {"document_id": "d1", "folder_token": "fld_team_a"},
        },
    )
    assert r.status_code == 400
    assert "unknown" in (r.json().get("error") or "").lower()
    assert queue.calls == []


def test_url_verification_returns_challenge():
    settings = ExecutorSettings(
        feishu_encrypt_key="",
        feishu_verification_token="",
    )
    routing = RoutingConfig(
        pipeline_workspace=PipelineWorkspace(
            path="C:\\workspaces\\pipeline",
            cursor_timeout_seconds=7200,
        ),
        folder_routes=[
            FolderRoute(
                folder_token="fld_team_a",
                qa_rule_file="rules/team_a_qa.md",
                dataset_id="dataset_team_a",
            )
        ],
    )
    queue = FakeQueue()
    store = RedisStateStore(redis_client=FakeStrictRedis(decode_responses=True))
    app = create_app(
        settings=settings,
        routing_config=routing,
        state_store=store,
        queue=queue,
    )
    client = TestClient(app)

    response = client.post(
        "/webhook/feishu",
        json={"type": "url_verification", "challenge": "abc"},
    )

    assert response.status_code == 200
    assert response.json() == {"challenge": "abc"}


def test_url_verification_rejects_invalid_verification_token():
    settings = ExecutorSettings(
        feishu_encrypt_key="",
        feishu_verification_token="expected-token",
    )
    routing = RoutingConfig(
        pipeline_workspace=PipelineWorkspace(
            path="C:\\workspaces\\pipeline",
            cursor_timeout_seconds=7200,
        ),
        folder_routes=[
            FolderRoute(
                folder_token="fld_team_a",
                qa_rule_file="rules/team_a_qa.md",
                dataset_id="dataset_team_a",
            )
        ],
    )
    queue = FakeQueue()
    store = RedisStateStore(redis_client=FakeStrictRedis(decode_responses=True))
    app = create_app(
        settings=settings,
        routing_config=routing,
        state_store=store,
        queue=queue,
    )
    client = TestClient(app)

    response = client.post(
        "/webhook/feishu",
        json={
            "type": "url_verification",
            "challenge": "abc",
            "token": "wrong-token",
        },
    )

    assert response.status_code == 403
    assert response.json() == {"error": "invalid verification token"}


def test_bad_body_returns_400():
    settings = ExecutorSettings(
        feishu_encrypt_key="",
        feishu_verification_token="",
    )
    routing = RoutingConfig(
        pipeline_workspace=PipelineWorkspace(
            path="C:\\workspaces\\pipeline",
            cursor_timeout_seconds=7200,
        ),
        folder_routes=[
            FolderRoute(
                folder_token="fld_team_a",
                qa_rule_file="rules/team_a_qa.md",
                dataset_id="dataset_team_a",
            )
        ],
    )
    queue = FakeQueue()
    store = RedisStateStore(redis_client=FakeStrictRedis(decode_responses=True))
    app = create_app(
        settings=settings,
        routing_config=routing,
        state_store=store,
        queue=queue,
    )
    client = TestClient(app)

    response = client.post("/webhook/feishu", content=b"{not-json")

    assert response.status_code == 400
    assert response.json() == {"error": "bad body"}


def test_build_app_wraps_rq_queue_with_adapter(monkeypatch):
    settings = ExecutorSettings()
    routing = RoutingConfig(
        pipeline_workspace=PipelineWorkspace(
            path="C:\\workspaces\\pipeline",
            cursor_timeout_seconds=7200,
        ),
        folder_routes=[
            FolderRoute(
                folder_token="fld_team_a",
                qa_rule_file="rules/team_a_qa.md",
                dataset_id="dataset_team_a",
            )
        ],
    )
    fake_redis = object()
    fake_queue = object()
    fake_adapter = FakeQueue()
    captured = {}

    monkeypatch.setattr(
        "webhook_cursor_executor.app.get_executor_settings",
        lambda: settings,
    )
    monkeypatch.setattr(
        "webhook_cursor_executor.app.load_routing_config",
        lambda _: routing,
    )
    monkeypatch.setattr(
        "webhook_cursor_executor.app.Redis.from_url",
        lambda *args, **kwargs: fake_redis,
    )
    monkeypatch.setattr(
        "webhook_cursor_executor.app.Queue",
        lambda *args, **kwargs: fake_queue,
    )

    def fake_rq_queue_adapter(*, queue):
        captured["queue"] = queue
        return fake_adapter

    monkeypatch.setattr(
        "webhook_cursor_executor.app.RQQueueAdapter",
        fake_rq_queue_adapter,
    )

    app = build_app()

    assert app.title == "Webhook Cursor Executor"
    assert captured["queue"] is fake_queue
