from pathlib import Path
from unittest.mock import ANY, call, patch

from bootstrap.install_workspace_editables import install_workspace_editables


def test_install_workspace_editables_invokes_pip_in_order(tmp_path):
    ws = tmp_path / "w"
    dirs = (
        ws / "vla_env_contract",
        ws / "runtime" / "webhook",
        ws / "tools" / "dify_upload",
        ws / "tools" / "feishu_fetch",
    )
    for d in dirs:
        d.mkdir(parents=True)

    with patch("bootstrap.install_workspace_editables.subprocess.run") as run:
        install_workspace_editables(ws)

    assert run.call_count == 4
    c0, c1, c2, c3 = run.call_args_list
    assert c0 == call(
        [ANY, "-m", "pip", "install", "-e", "."],
        check=True,
        cwd=str(dirs[0]),
    )
    assert c1.kwargs["cwd"] == str(dirs[1])
    assert c2.kwargs["cwd"] == str(dirs[2])
    assert c3.kwargs["cwd"] == str(dirs[3])
