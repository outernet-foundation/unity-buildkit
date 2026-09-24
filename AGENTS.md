# unity-devkit

## What this is

`unity-devkit` is the Unity build toolkit: project discovery, local builds, CI builds, license activation, the `install` command (download-or-build then install onto a device), and the ORAS cache/setup helpers those need. Consumer repositories install this package from PyPI and get the same Unity CI and install flow — paired with the reusable `unity-build.yml` GitHub Actions workflow hosted in this repo's `.github/workflows/`, which invokes only this package's entry points inside the caller's checkout.

The repo and package renamed from `unity-buildkit` to `unity-devkit` (2026-09-21, member of the `-devkit` family; before that `placeframe-unity` → `unity-buildkit` on extraction). The PyPI identity is fresh: `unity-devkit` starts its own tag ledger at `0.1.0`; the terminal `unity-buildkit` distributions (≤0.1.1) are deprecation signposts pointing here, not this package's history.

## Release flow

Publishing rides `release.yml`, triggered by a successful CI run on a `main` push: the machinery — release-devkit's `publish-stable` (an inlined, version-pinned `uvx` step in the publish job, keeping OIDC identity local), never a project dependency (unity-devkit sits inside its own dependency graph; a project-level release-devkit edge is a resolver cycle) — computes the plan from the tag ledger and path-diff, patches the version ephemerally, and publishes to PyPI under OIDC trusted publishing (publisher bound to `release.yml`, no environment). The committed `pyproject.toml` version is permanently the `0.0.0.dev0` sentinel; the `unity-devkit-v*` tags are the version ledger (declared `major_minor` line in `publish-config.json`, patch-auto within the line). API-breaking changes ship with a manually bumped `major_minor` — patch-auto assumes additive changes.

## Shape

One flat module per concern under `src/unity_devkit/`:

| `uv run` command | Module | Notes |
|---|---|---|
| `compile-unity` | `compile_unity.py` | Local Unity build (APK or platform binary, suitable for `adb install`). Required flags: `--project <name>` and `--build <target>`, where the project's `unity-build.json` declares `builds` and `execute_methods`. Streams the editor log, prints output paths under `<project>/Build/`. |
| `install` | `install.py` | Install a Unity build onto an `adb`-connected device or launch a linux executable. Default: download the latest GitHub Actions artifact for `(project, target)` on the current branch (overridable with `--branch` / `--run`), cache it under `~/.unity-devkit/builds/{run_id}/`, `adb install` the APK (or `bash_handoff` the linux64 executable). With `--build` / `-B`, skips the artifact fetch and calls `compile-unity` locally instead, funneling the produced APK / executable through the same install path. Honours the manifest's `package` (for pre-install uninstall) and `grant_permissions` (post-install `adb shell pm grant`). |
| `lock-unity` | `lock_unity.py` | Lock Unity package versions for reproducible builds. |
| `test-unity` | `test_unity.py` | Run Unity editmode / playmode tests. |
| `activate-unity-license` | `license.py` | Activate the Unity Editor license (locally or with `--oras-push` for the CI cache). |
| `unity-license-tag` | `license_restore.py` | Print the license cache tag (CI pins it via `LICENSE_CACHE_TAG`). |
| `unity-matrix` | `matrix.py` | Emit the CI build matrix (CI-only). |
| `build-unity` | `build_unity.py` | CI build with library cache restore/save and version stamping (CI-only; assumes `GITHUB_WORKSPACE`, OCI registry, runner environment). |

Supporting modules: `projects.py` (manifest schema + discovery), `unity.py` (editor lookup, platform configs, batchmode command, shared Unity runner). The CI-floor modules (step wrapper, runner provisioning, ORAS artifact cache, git-tag helpers) live in [`ci-devkit`](https://github.com/outernet-foundation/ci-devkit) (a runtime dependency); unity-devkit owns only Unity concerns.

## Constraints

**Every Unity invocation goes through `unity.run_unity_batchmode`, which does not trust the editor's exit code.** Unity exits 0 while reporting fatal package-manager errors (unresolvable dependencies, invalid package.json versions) only in the editor log — a resolver failure therefore surfaces as a stale `packages-lock.json` and nothing else. The runner streams the log live through `tee` into a captured file and afterwards scans it for `QUIET_FAILURE_SIGNATURES`; a match fails the invocation with the matched log block regardless of exit code. New Unity verbs must call the runner rather than invoking the editor directly, and newly discovered silent-failure log lines get added to the signature tuple. Exit-code strictness is per-verb: build/test verbs fail on non-zero (`strict_exit=True`, the default), while `lock-unity` passes `strict_exit=False` — it judges resolution, not compilation, so a project whose scripts fail to compile (resolution already done, lock written) produces a warning, not a failure. `-runTests` invocations pass `auto_quit=False` (the test runner owns exit timing).

**Every runtime dependency must be PyPI-resolvable.** This package publishes to and is consumed from PyPI, and a registry consumer resolves the whole graph transitively by name — any dependency that is not on PyPI breaks every consumer's install. [`bashrun`](https://github.com/outernet-foundation/bashrun) is on PyPI like the rest; git-source pins are a scratch-branch-only vehicle for testing unreleased changes.

**Unity project discovery is structural, with `unity-build.json` as an optional intent overlay.** The Unity commands discover projects by scanning the working-directory tree for `ProjectSettings/ProjectVersion.txt` (pruning `Library`, `Temp`, `obj`, `Build`, `node_modules`, `.git`, and dot-directories) — the marker Unity itself writes, so existence needs no opt-in file. The project name is the directory name. A `unity-build.json` manifest beside it carries only intent the project cannot otherwise express (`builds`, `execute_methods`, `package`, `grant_permissions`, `tag_prefix` — schema in `projects.py`); it is required by the verbs that consume those fields (`compile-unity`, `build-unity`, `install`, `unity-matrix` — which fail with pointers to the missing manifest fields) and ignored by the path-only verbs (`lock-unity`, `test-unity`). A manifest found in a directory without the structural marker is a hard error — a misconfigured manifest must fail loud, not silently skip. There is no central catalog: a project's build identity lives inside the project, so it travels with the project if it moves between repositories. Discovery anchors at the current working directory — run commands from the repo root. Vendored or nested projects that should not be touched are kept out of all-projects verbs (`lock-unity`, `test-unity` without `--project`) by the prune list or by passing `--project` explicitly.

**`unity-matrix` prints `$GITHUB_OUTPUT`-format lines, not bare JSON.** Its stdout is two `key=value` lines — `matrix=<JSON with an include array>` and `license-image=<unityci/editor tag>` — so the workflow step is exactly `uv run --no-sync unity-matrix >> "$GITHUB_OUTPUT"` with no shell logic. Each matrix entry carries an `editor-image` tag composed from the project's `ProjectSettings/ProjectVersion.txt` editor version, the platform's unityci module, and the `UNITYCI_IMAGE_REVISION` constant in `unity.py`; `license-image` uses the highest discovered editor version with the `linux-il2cpp` module. Nothing else pins an editor version: upgrading a project's editor in `ProjectVersion.txt` automatically switches its CI container, and the hosted `unity-build.yml` stays free of repo-specific values.

**Entry-point names are the workflow contract.** The hosted `unity-build.yml` invokes `unity-matrix`, `unity-license-tag`, `activate-unity-license`, and `build-unity` by name via `uv run` in the caller's checkout (the caller's venv supplies this package). Consumers pin the workflow by pushed SHA and the package by PyPI version independently; the two pins stay compatible as long as the entry-point names and flags hold, so treat those as a public API.

**The environment-lookup helpers are cross-repo Python API.** `unity.find_editor_for_version` (editor ladder: `unity-editor` on PATH → `/opt/unity/<version>` → `~/Unity/Hub/Editor/<version>`; raises `ValueError` listing every searched path on a miss), `unity.editor_version` (`ProjectVersion.txt` parse; `None` for a missing file or unparseable content), and `projects.directories_containing` (+ `PRUNE_DIRECTORIES`) are imported by registry consumers — prepo's `sync` verb. Their signatures and miss behavior are contract, not internals. The `SystemExit`-raising wrapper `read_editor_version` exists for unity-devkit's own CLI paths and delegates to the core helper; `unity_batchmode_command` consumes the `ValueError`-raising `find_editor_for_version` and `read_editor_version` directly, so a missing editor surfaces as the raw `ValueError`.

**Version stamping is opt-in via `tag_prefix`.** `build-unity` writes `.build-version.json` (consumed by the project's build `executeMethod`) only when the project's manifest declares `tag_prefix`; the version is the latest `<tag_prefix>-v*` git tag plus a run-number suffix. Projects without the field build unversioned. Consumer repos that release keep their own name→prefix map on their side — the two must agree for projects that release.

**The ORAS cache media type identifies the wrapper package, not the consuming repo.** `cache.save()` pushes with `application/vnd.unity-devkit.cache.v1+zstd`. Restore doesn't filter on media type, so older manifests carrying a different vendor prefix still pull, but new pushes always carry this one — the identifier tracks the tool that wrote the cache, not the project whose bytes are inside it.

## See also

- [`bashrun`](https://github.com/outernet-foundation/bashrun) — the shell-exec helpers this package uses everywhere (`bash`, `bash_output`, `bash_check`, `bash_handoff`).
- `README.md` — human-facing setup, command catalog, and consumer install snippet.
