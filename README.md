# unity-buildkit

Unity project discovery, local builds, CI builds, license activation, and the shared CI helpers those need. Consumers scan the working-directory tree for `unity-build.json` manifests to enumerate their Unity projects; the commands here (`compile-unity`, `install`, `build-unity`, `unity-matrix`, license helpers) work unchanged in any repo containing manifests. Paired with the reusable [`unity-build.yml`](https://github.com/outernet-foundation/unity-buildkit/blob/main/.github/workflows/unity-build.yml) GitHub Actions workflow (once the workflow lands here — until then, workflow YAML lives in consumer repos).

## Setup

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

## Commands

Run from a repo root containing one or more `unity-build.json` manifests.

| `uv run <name>` | What it does |
|---|---|
| `compile-unity --project <name> --build <target>` | Local Unity build (APK or platform binary) suitable for `adb install`. |
| `install --project <name>` | Download the latest CI artifact and `adb install` (or launch, for `linux64`); with `--build`, compile locally first. |
| `lock-unity` | Lock Unity package versions. |
| `test-unity --project <name>` | Run editmode / playmode tests. |
| `activate-unity-license` | Activate the Unity Editor license (locally or with `--oras-push`). |
| `unity-license-tag` | Print the license cache tag. |
| `unity-matrix` | Emit the CI build matrix (CI-only; two `key=value` lines for `$GITHUB_OUTPUT`). |
| `build-unity` | CI build with library-cache restore/save and version stamping (CI-only). |

Every command accepts `--help`.

## Consuming from another repo

git-reference this package and `bashrun` (its only non-PyPI dependency) from your own `pyproject.toml`:

```toml
[project]
dependencies = ["unity-buildkit"]

[tool.uv.sources]
unity-buildkit = { git = "https://github.com/outernet-foundation/unity-buildkit.git", rev = "<pin-a-commit-sha>" }
bashrun = { git = "https://github.com/outernet-foundation/bashrun.git", rev = "<pin-a-commit-sha>" }
```

Then `uv run compile-unity`, `uv run install`, etc. work from that repo against its own `unity-build.json` projects.

## Development

```bash
uv run ruff check .
uv run ruff format --check .
uv run basedpyright
```
