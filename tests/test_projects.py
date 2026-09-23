import json
from pathlib import Path

import pytest

from unity_devkit.projects import load_unity_projects


def create_unity_project(root: Path, name: str, manifest: dict[str, object] | None = None) -> Path:
    project = root / name
    (project / "ProjectSettings").mkdir(parents=True)
    (project / "ProjectSettings" / "ProjectVersion.txt").write_text("m_EditorVersion: 6000.0.66f1\n")
    if manifest is not None:
        (project / "unity-build.json").write_text(json.dumps(manifest))
    return project


def test_structural_project_without_manifest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    create_unity_project(tmp_path, "Alpha")
    monkeypatch.chdir(tmp_path)

    projects = load_unity_projects()

    assert set(projects) == {"Alpha"}
    assert projects["Alpha"].path == tmp_path.resolve() / "Alpha"
    assert projects["Alpha"].builds is None


def test_manifest_overlays_structural_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    create_unity_project(tmp_path, "Alpha", {"builds": ["linux64"], "tag_prefix": "alpha"})
    monkeypatch.chdir(tmp_path)

    projects = load_unity_projects()

    assert projects["Alpha"].builds == ["linux64"]
    assert projects["Alpha"].tag_prefix == "alpha"


def test_stray_manifest_outside_unity_project_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    stray = tmp_path / "Beta"
    stray.mkdir()
    (stray / "unity-build.json").write_text("{}")
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit, match="not inside a Unity project"):
        load_unity_projects()


def test_no_projects_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit, match="No Unity projects found"):
        load_unity_projects()


def test_duplicate_project_names_fail(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    create_unity_project(tmp_path / "site-a", "Alpha")
    create_unity_project(tmp_path / "site-b", "Alpha")
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit, match="Duplicate Unity project name"):
        load_unity_projects()


def test_pruned_directories_are_skipped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    vendored = tmp_path / "vendor" / "Library" / "SomeProject"
    (vendored / "ProjectSettings").mkdir(parents=True)
    (vendored / "ProjectSettings" / "ProjectVersion.txt").write_text("m_EditorVersion: 6000.0.66f1\n")
    create_unity_project(tmp_path, "Real")
    monkeypatch.chdir(tmp_path)

    projects = load_unity_projects()

    assert set(projects) == {"Real"}
