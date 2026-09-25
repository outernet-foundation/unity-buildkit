from pathlib import Path

import pytest
from bashrun.bash import bash

from unity_devkit.build_unity import latest_tag_version


def test_latest_tag_version_returns_newest_version_sorted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    bash("git init -q")
    bash("git config user.email test@example.com")
    bash("git config user.name test")
    bash("git commit --allow-empty -m init -q")
    for version in ("0.1.2", "0.1.9", "0.1.10"):
        bash(f"git tag thing-v{version}")

    assert latest_tag_version("thing-v") == "0.1.10"
    assert latest_tag_version("absent-v") is None
