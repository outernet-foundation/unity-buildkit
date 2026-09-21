import json
import os
from pathlib import Path

from pydantic import BaseModel

MANIFEST_FILENAME = "unity-build.json"
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
    projects: dict[str, UnityProject] = {}
    for directory in directories_containing(Path.cwd(), MANIFEST_FILENAME):
        project_path = directory.resolve()
        name = project_path.name
        version_file = project_path / "ProjectSettings" / "ProjectVersion.txt"
        if not version_file.exists():
            raise SystemExit(
                f"{project_path / MANIFEST_FILENAME} is not inside a Unity project: missing {version_file}"
            )
        if name in projects:
            raise SystemExit(f"Duplicate Unity project name '{name}': {projects[name].path} and {project_path}")

        manifest = UnityBuildManifest(**json.loads((project_path / MANIFEST_FILENAME).read_text()))
        projects[name] = UnityProject(path=project_path, **manifest.model_dump())

    if not projects:
        raise SystemExit(f"No {MANIFEST_FILENAME} manifests found under {Path.cwd()} — run from the repo root")

    return projects


def directories_containing(root: Path, filename: str) -> list[Path]:
    directories: list[Path] = []
    for directory, subdirectories, filenames in os.walk(root):
        subdirectories[:] = sorted(
            name for name in subdirectories if name not in PRUNE_DIRECTORIES and not name.startswith(".")
        )
        if filename in filenames:
            directories.append(Path(directory))
    return directories
