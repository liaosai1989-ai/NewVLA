from pathlib import Path

from feishu_onboard import env_store


def test_load_parse_roundtrip_preserves_comment(tmp_path: Path) -> None:
    p = tmp_path / ".env"
    p.write_text("# keep\nFOO=1\n", encoding="utf-8")
    m = env_store.load_flat_map(p)
    assert m["FOO"] == "1"
    env_store.set_keys_atomic(p, {"FOO": "2"}, create_backup=False)
    text = p.read_text(encoding="utf-8")
    assert "# keep" in text
    assert "FOO=2" in text


def test_set_dedup_same_key(tmp_path: Path) -> None:
    p = tmp_path / ".env"
    p.write_text("A=1\nA=2\n", encoding="utf-8")
    env_store.set_keys_atomic(p, {"A": "3"}, create_backup=False)
    assert p.read_text(encoding="utf-8").count("A=") == 1
    m = env_store.load_flat_map(p)
    assert m["A"] == "3"


def test_load_duplicate_key_last_line_wins(tmp_path: Path) -> None:
    p = tmp_path / ".env"
    p.write_text("A=1\nA=2\n", encoding="utf-8")
    assert env_store.load_flat_map(p)["A"] == "2"


def test_load_bom_quoted_credential_stripped(tmp_path: Path) -> None:
    p = tmp_path / ".env"
    p.write_bytes(
        b"\xef\xbb\xbf" b'K="v"\n' b"K2= 'x' \n" b"A=b\n"  # utf-8 BOM + 可选引号
    )
    m = env_store.load_flat_map(p)
    assert m["K"] == "v"
    assert m["K2"] == "x"  # 外层单引号
    assert m["A"] == "b"  # 无引号
