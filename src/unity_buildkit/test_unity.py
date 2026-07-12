from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Annotated

import typer
from bashrun import bash

from .projects import load_unity_projects
from .unity import find_unity_editor

app = typer.Typer(add_completion=False, pretty_exceptions_show_locals=False)


@app.command()
def main(
    project: Annotated[str, typer.Option(help="Unity project name (directory containing unity-build.json)")],
    test_platform: Annotated[str, typer.Option(help="Unity test platform (EditMode or PlayMode)")] = "EditMode",
    results: Annotated[Path, typer.Option(help="Output path for NUnit XML results")] = Path(
        "artifacts/unity-test-results.xml"
    ),
) -> None:
    projects = load_unity_projects()
    if project not in projects:
        raise SystemExit(f"Unknown project '{project}'. Valid: {', '.join(projects)}")

    project_path = projects[project].path
    editor = find_unity_editor(project_path)
    results.parent.mkdir(parents=True, exist_ok=True)

    command = (
        f"{editor} -batchmode -nographics -projectPath {project_path}"
        f" -runTests -testPlatform {test_platform} -testResults {results.resolve()} -logFile -"
    )
    if sys.platform != "win32" and shutil.which("xvfb-run"):
        command = f"xvfb-run {command}"
    bash(command)
