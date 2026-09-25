import json
from pathlib import Path

import pytest

from unity_devkit import matrix


def write_repository(tmp_path: Path, entry: dict[str, object]) -> None:
    project = tmp_path / "apps" / "Tool"
    (project / "ProjectSettings").mkdir(parents=True)
    (project / "ProjectSettings" / "ProjectVersion.txt").write_text("m_EditorVersion: 6000.0.66f1\n")
    (tmp_path / "unity-devkit.json").write_text(json.dumps({"tool": entry}))


def test_matrix_emits_entries_from_catalog(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    write_repository(
        tmp_path, {"path": "apps/Tool", "builds": ["linux64"], "execute_methods": {"linux64": "Tool.Build"}}
    )
    monkeypatch.chdir(tmp_path)

    matrix.main()

    lines = capsys.readouterr().out.splitlines()
    include = json.loads(lines[0][len("matrix=") :])["include"]
    assert include == [
        {
            "project": str(Path("apps") / "Tool"),
            "project-name": "tool",
            "cache-key": "tool",
            "platform": "linux64",
            "module": "linux-il2cpp",
            "editor-image": "unityci/editor:6000.0.66f1-linux-il2cpp-3",
        }
    ]
    assert lines[1] == "license-image=unityci/editor:6000.0.66f1-linux-il2cpp-3"


def test_matrix_fails_without_builds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    write_repository(tmp_path, {"path": "apps/Tool"})
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit, match="No projects with builds declared"):
        matrix.main()
