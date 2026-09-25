import json
from pathlib import Path

from .projects import load_catalog
from .unity import LICENSE_MODULE, PLATFORM_CONFIGS, UNITYCI_IMAGE_REVISION, read_editor_version


def main() -> None:
    projects = load_catalog()
    matrix: list[dict[str, str]] = []
    editor_versions: set[str] = set()

    for name, project in projects.items():
        if not project.builds:
            continue
        version = read_editor_version(project.path)
        editor_versions.add(version)
        for platform in project.builds:
            module = PLATFORM_CONFIGS[platform]["module"]
            matrix.append({
                "project": str(project.path.relative_to(Path.cwd())),
                "project-name": name,
                "cache-key": name.lower(),
                "platform": platform,
                "module": module,
                "editor-image": f"unityci/editor:{version}-{module}-{UNITYCI_IMAGE_REVISION}",
            })

    if not editor_versions:
        raise SystemExit(
            "No projects with builds declared — unity-matrix needs at least one unity-devkit.json entry with a 'builds' list"
        )
    license_version = max(editor_versions)
    print(f"matrix={json.dumps({'include': matrix})}")
    print(f"license-image=unityci/editor:{license_version}-{LICENSE_MODULE}-{UNITYCI_IMAGE_REVISION}")
