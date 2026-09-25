import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from unity_devkit.projects import directories_containing, load_catalog


def write_catalog(root: Path, catalog: dict[str, object]) -> Path:
    catalog_path = root / "unity-devkit.json"
    catalog_path.write_text(json.dumps(catalog))
    return catalog_path


def create_unity_project(root: Path, relative: str) -> Path:
    project = root / relative
    (project / "ProjectSettings").mkdir(parents=True)
    (project / "ProjectSettings" / "ProjectVersion.txt").write_text("m_EditorVersion: 6000.0.66f1\n")
    return project


def test_catalog_entry_loads_with_intent_fields(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    create_unity_project(tmp_path, "Alpha")
    write_catalog(tmp_path, {"Alpha": {"path": "Alpha", "builds": ["linux64"], "tag_prefix": "alpha"}})
    monkeypatch.chdir(tmp_path)

    projects = load_catalog()

    assert set(projects) == {"Alpha"}
    assert projects["Alpha"].path == Path.cwd() / "Alpha"
    assert projects["Alpha"].builds == ["linux64"]
    assert projects["Alpha"].tag_prefix == "alpha"
    assert projects["Alpha"].grant_permissions == []


def test_catalog_name_is_decoupled_from_directory_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    create_unity_project(tmp_path, "apps/capture-tool")
    write_catalog(tmp_path, {"capture": {"path": "apps/capture-tool"}})
    monkeypatch.chdir(tmp_path)

    projects = load_catalog()

    assert set(projects) == {"capture"}
    assert projects["capture"].path == Path.cwd() / "apps" / "capture-tool"


def test_missing_catalog_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit, match=r"No unity-devkit\.json catalog"):
        load_catalog()


def test_empty_catalog_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    write_catalog(tmp_path, {})
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit, match="declares no projects"):
        load_catalog()


def test_entry_outside_unity_project_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "not-a-project").mkdir()
    write_catalog(tmp_path, {"broken": {"path": "not-a-project"}})
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit, match="not a Unity project"):
        load_catalog()


def test_unknown_entry_key_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    create_unity_project(tmp_path, "Alpha")
    write_catalog(tmp_path, {"Alpha": {"path": "Alpha", "unity-build": True}})
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValidationError):
        load_catalog()


def test_directories_containing_honors_prune_list(tmp_path: Path) -> None:
    vendored = tmp_path / "vendor" / "Library" / "SomeProject"
    (vendored / "ProjectSettings").mkdir(parents=True)
    (vendored / "ProjectSettings" / "ProjectVersion.txt").write_text("m_EditorVersion: 6000.0.66f1\n")
    real = create_unity_project(tmp_path, "Real")

    settings_directories = directories_containing(tmp_path, "ProjectVersion.txt")

    assert real / "ProjectSettings" in settings_directories
    assert vendored / "ProjectSettings" not in settings_directories
