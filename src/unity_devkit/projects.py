import os
from collections.abc import Iterator
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator

CATALOG_FILENAME = "unity-devkit.json"
PROJECT_MARKER = Path("ProjectSettings") / "ProjectVersion.txt"
PRUNE_DIRECTORIES = {".git", "Library", "Temp", "obj", "Build", "node_modules", "__pycache__"}


class CatalogEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: Path
    builds: list[str] | None = None
    execute_methods: dict[str, str] | None = None
    package: str | None = None
    grant_permissions: list[str] = Field(default_factory=list)
    tag_prefix: str | None = None

    @field_validator("path")
    @classmethod
    def anchor_relative_path(cls, value: Path) -> Path:
        return value if value.is_absolute() else Path.cwd() / value


CATALOG_ADAPTER = TypeAdapter(dict[str, CatalogEntry])


def load_catalog() -> dict[str, CatalogEntry]:
    catalog_path = Path.cwd() / CATALOG_FILENAME
    if not catalog_path.is_file():
        raise SystemExit(
            f"No {CATALOG_FILENAME} catalog at {catalog_path} — declare Unity projects as catalog entries at the repo root"
        )

    catalog = CATALOG_ADAPTER.validate_json(catalog_path.read_text(encoding="utf-8"))
    if not catalog:
        raise SystemExit(f"{catalog_path} declares no projects — at least one catalog entry is required")

    for name, entry in catalog.items():
        if not (entry.path / PROJECT_MARKER).is_file():
            raise SystemExit(
                f"Catalog entry '{name}' points at {entry.path}, which is not a Unity project: missing {PROJECT_MARKER}"
            )
    return catalog


def visible_directories(root: Path) -> Iterator[Path]:
    for directory, subdirectories, _filenames in os.walk(root):
        subdirectories[:] = sorted(
            name for name in subdirectories if name not in PRUNE_DIRECTORIES and not name.startswith(".")
        )
        yield Path(directory)


def directories_containing(root: Path, filename: str) -> list[Path]:
    return [directory for directory in visible_directories(root) if (directory / filename).is_file()]
