from pathlib import Path

from bootstrap.env_dotenv import read_env_keys


def test_read_env_keys(tmp_path):
    p = tmp_path / ".env"
    p.write_text(
        "# x\nREDIS_URL=redis://localhost:6379/0\n"
        "FOLDER_ROUTES_FILE=webhook/config/routes.json\n",
        encoding="utf-8",
    )
    keys = read_env_keys(p)
    assert keys["REDIS_URL"] == "redis://localhost:6379/0"
    assert keys["FOLDER_ROUTES_FILE"] == "webhook/config/routes.json"
