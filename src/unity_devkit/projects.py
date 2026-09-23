import json
import os
from collections.abc import Iterator
from pathlib import Path

from pydantic import BaseModel

MANIFEST_FILENAME = "unity-build.json"
PROJECT_MARKER = Path("ProjectSettings") / "ProjectVersion.txt"
PRUNE_DIRECTORIES = {".git", "Library", "Temp", "obj", "Build", "node_modules", "__pycache__"}


class UnityBuildManifest(BaseModel, extra="forbid"):
    builds: list[str] | None = None
    execute_methods: dict[str, str] | None = None
    package: str | None = None
    grant_permissions: list[str] = []
    tag_prefix: str | None = None


class UnityProject(UnityBuildManifest):
    path: Path


def load_unity_projects() -> dict[str, UnityProject]:
    root = Path.cwd()
    project_directories = {directory.resolve() for directory in unity_project_directories(root)}
    manifest_directories = {directory.resolve() for directory in directories_containing(root, MANIFEST_FILENAME)}

    projects: dict[str, UnityProject] = {}
    for project_path in sorted(project_directories | manifest_directories):
        if project_path not in project_directories:
            raise SystemExit(
                f"{project_path / MANIFEST_FILENAME} is not inside a Unity project: missing {PROJECT_MARKER}"
            )

        manifest_path = project_path / MANIFEST_FILENAME
        if manifest_path.exists():
            manifest = UnityBuildManifest(**json.loads(manifest_path.read_text()))
        else:
            manifest = UnityBuildManifest()

        name = project_path.name
        if name in projects:
            raise SystemExit(f"Duplicate Unity project name '{name}': {projects[name].path} and {project_path}")
        projects[name] = UnityProject(path=project_path, **manifest.model_dump())

    if not projects:
        raise SystemExit(
            f"No Unity projects found under {root} — a project is a directory containing {PROJECT_MARKER}. Run from the repo root"
        )
    return projects


def visible_directories(root: Path) -> Iterator[Path]:
    for directory, subdirectories, _filenames in os.walk(root):
        subdirectories[:] = sorted(
            name for name in subdirectories if name not in PRUNE_DIRECTORIES and not name.startswith(".")
        )
        yield Path(directory)


def unity_project_directories(root: Path) -> list[Path]:
    return [directory for directory in visible_directories(root) if (directory / PROJECT_MARKER).is_file()]


def directories_containing(root: Path, filename: str) -> list[Path]:
    return [directory for directory in visible_directories(root) if (directory / filename).is_file()]
