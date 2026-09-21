from typing import Annotated

import typer

from .projects import load_unity_projects
from .unity import prepare_unity_project, run_unity_batchmode

app = typer.Typer(add_completion=False, pretty_exceptions_show_locals=False)


@app.command()
def lock_unity(project: Annotated[str | None, typer.Option(help="Limit to a specific project.")] = None) -> None:
    config = load_unity_projects()

    if project is not None and project not in config:
        raise typer.BadParameter(f"Unknown project '{project}'. Valid: {', '.join(config)}")

    all_projects = {name: project_config.path for name, project_config in config.items()}
    projects = {project: all_projects[project]} if project else all_projects

    for name, project_path in projects.items():
        lock_file = project_path / "Packages" / "packages-lock.json"
        print(f"Resolving {name} ({lock_file})...")

        prepare_unity_project(project_path)
        run_unity_batchmode(project_path, strict_exit=False)

        print("  Done")
