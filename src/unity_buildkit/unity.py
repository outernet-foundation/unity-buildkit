import shutil
import sys
import tempfile
from pathlib import Path
from typing import TypedDict

from bashrun import CalledProcessError, bash, bash_pipe

from .projects import UnityProject, load_unity_projects


class PlatformConfig(TypedDict):
    build_flag: str
    module: str


PLATFORM_CONFIGS: dict[str, PlatformConfig] = {
    "android-mobile": {"build_flag": "-buildTarget Android", "module": "android"},
    "magicleap": {"build_flag": "-buildTarget Android", "module": "android"},
    "linux64": {"build_flag": "-buildTarget StandaloneLinux64", "module": "linux-il2cpp"},
    "win64": {"build_flag": "-buildTarget Win64", "module": "windows-mono"},
}

UNITYCI_IMAGE_REVISION = "3"
LICENSE_MODULE = "linux-il2cpp"

# Unity exits 0 while reporting fatal package-manager errors only in the editor log. Every
# Unity invocation goes through run_unity_batchmode, which scans the captured log for these
# signatures and fails regardless of the exit code. Extend the tuple as new silent failures
# are discovered.
QUIET_FAILURE_SIGNATURES = ("An error occurred while resolving packages:",)
QUIET_FAILURE_BLOCK_LINE_LIMIT = 20


def find_unity_editor(project_path: Path) -> str:
    try:
        editor = find_editor_for_version(read_editor_version(project_path))
    except ValueError as error:
        raise SystemExit(str(error)) from error
    return str(editor)


def find_editor_for_version(version: str) -> Path:
    path_editor = shutil.which("unity-editor")
    if path_editor:
        return Path(path_editor)

    if sys.platform == "win32":
        candidates = [Path(f"C:/Program Files/Unity/Hub/Editor/{version}/Editor/Unity.exe")]
    else:
        candidates = [
            Path(f"/opt/unity/{version}/Editor/Unity"),
            Path.home() / f"Unity/Hub/Editor/{version}/Editor/Unity",
        ]

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    searched = ", ".join(str(candidate) for candidate in candidates)
    raise ValueError(f"Cannot find Unity {version} editor. Searched: {searched}")


def read_editor_version(project_path: Path) -> str:
    version_file = project_path / "ProjectSettings" / "ProjectVersion.txt"
    version = editor_version(project_path)
    if version is not None:
        return version
    if not version_file.exists():
        raise SystemExit(f"Cannot find {version_file} — is this a Unity project?")
    raise SystemExit(f"Cannot parse editor version from {version_file}")


def editor_version(project_path: Path) -> str | None:
    version_file = project_path / "ProjectSettings" / "ProjectVersion.txt"
    if not version_file.exists():
        return None
    for line in version_file.read_text().splitlines():
        if line.startswith("m_EditorVersion:"):
            return line.split(":", 1)[1].strip()
    return None


def prepare_unity_project(project_path: Path) -> None:
    stale_lockfile = project_path / "Temp" / "UnityLockfile"
    if stale_lockfile.exists():
        stale_lockfile.unlink()

    bash("dotnet tool restore")
    bash(f"dotnet nugetforunity restore {project_path}")


def unity_batchmode_command(project_path: Path, nographics: bool = True, *, auto_quit: bool = True) -> str:
    editor = find_unity_editor(project_path)
    # Player builds need a real GfxDevice: Unity 6 compresses Android textures (ASTC/ETC2) on the
    # GPU, and under -nographics the Null device falls back to a path that produces corrupt textures.
    # xvfb-run (added below) supplies the display the dropped -nographics would otherwise stand in for.
    graphics_flag = " -nographics" if nographics else ""
    quit_flag = " -quit" if auto_quit else ""
    command = f"{editor} -batchmode{graphics_flag}{quit_flag} -projectPath {project_path.resolve()}"
    if sys.platform != "win32":
        if shutil.which("xvfb-run"):
            command = f"xvfb-run {command}"
        # Unity runs `adb kill-server` on Android build teardown; strip the
        # env var so the kill lands on a local daemon, not whatever
        # ADB_SERVER_SOCKET points at.
        command = f"env -u ADB_SERVER_SOCKET {command}"
    return command


def run_unity_batchmode(
    project_path: Path,
    extra_flags: str = "",
    *,
    nographics: bool = True,
    auto_quit: bool = True,
    strict_exit: bool = True,
) -> None:
    log_path = Path(tempfile.mkdtemp(prefix="unity-buildkit-")) / "editor.log"
    command = (
        f"{unity_batchmode_command(project_path, nographics=nographics, auto_quit=auto_quit)} {extra_flags}"
    ).strip()
    command = f"{command} -logFile /dev/stdout"
    returncode = 0
    try:
        if shutil.which("tee"):
            bash_pipe(command, f"tee {log_path}")
        else:
            bash(command, log_path=log_path)
    except CalledProcessError as error:
        returncode = error.returncode
    failure_block = quiet_failure_block(log_path)
    if failure_block is not None:
        raise SystemExit(f"Unity reported a package-manager failure (exit code {returncode}):\n{failure_block}")
    if returncode != 0 and strict_exit:
        raise SystemExit(f"Unity exited {returncode}; full editor log at {log_path}")
    if returncode != 0:
        print(f"  WARNING: Unity exited {returncode}; no package-manager failure found — full editor log at {log_path}")


def quiet_failure_block(log_path: Path) -> str | None:
    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    for index, line in enumerate(lines):
        if not any(signature in line for signature in QUIET_FAILURE_SIGNATURES):
            continue
        block: list[str] = []
        for candidate in lines[index : index + QUIET_FAILURE_BLOCK_LINE_LIMIT]:
            if block and not candidate.strip():
                break
            block.append(candidate)
        return "\n".join(block)
    return None


def resolve_unity_build(project: str, build: str) -> tuple[UnityProject, str, str]:
    projects = load_unity_projects()
    if project not in projects:
        raise SystemExit(f"Unknown project '{project}'. Valid: {', '.join(projects)}")

    project_config = projects[project]
    valid_builds = project_config.builds or []
    if build not in valid_builds:
        valid = ", ".join(valid_builds) or "(none defined)"
        raise SystemExit(f"Unknown build '{build}' for project '{project}'. Valid: {valid}")

    execute_method = (project_config.execute_methods or {}).get(build)
    if not execute_method:
        raise SystemExit(f"No execute method for project '{project}' build '{build}'")

    if build not in PLATFORM_CONFIGS:
        raise SystemExit(f"No platform config for build '{build}'. Valid: {', '.join(PLATFORM_CONFIGS)}")

    return project_config, PLATFORM_CONFIGS[build]["build_flag"], execute_method
