---
hide:
  - navigation
---

# Releasing

This page is for project maintainers. If you're using siphyy, see [Install](../tutorial/install.md) instead.

A release is cut by pushing a `v*` tag. Everything after that is automated by `.github/workflows/release.yml`: build wheel + sdist, publish to PyPI via OIDC trusted publishing, create a GitHub Release with the changelog excerpt and the built artefacts attached.

## Versioning

We follow [SemVer](https://semver.org) with explicit alpha rules:

| Bump | Meaning during `0.x` | Meaning once `1.0+` |
|---|---|---|
| Patch — `0.1.0 → 0.1.1` | bug fixes, non-breaking improvements | same |
| Minor — `0.1.5 → 0.2.0` | **breaking changes are allowed here** | new features, non-breaking |
| Major — `0.x → 1.0` | first stable surface declared | breaking changes |

During 0.x, **tell users to pin with `~=0.1.0`**, not `>=0.1.0`. A minor bump can break adapters, detectors, or LLM client implementations.

Pre-release suffixes follow [PEP 440](https://peps.python.org/pep-0440/#pre-releases):

- `0.2.0a1` — alpha (rare; we mostly use plain version numbers during 0.x)
- `0.2.0b1` — beta
- `0.2.0rc1` — release candidate

PyPI treats anything with `a`/`b`/`rc` as a pre-release; `pip install siphyy` skips them unless `--pre` is passed or the version is explicitly pinned.

## Cutting a release

Six steps. The first four are manual; the rest is the workflow.

### 1. Pre-flight check

```bash
# On main, with a clean working tree:
git status                            # nothing pending
git pull origin main                  # latest
uv run pytest                         # green (skip integration)
uv run ruff check . && uv run ruff format --check .
uv run mypy src
uv run mkdocs build --strict          # docs build clean
```

If anything's red, fix it first. Don't tag from a dirty tree.

### 2. Update `CHANGELOG.md`

Promote the running `## [Unreleased]` section to a versioned, dated heading, and add a fresh empty `[Unreleased]` above it:

```diff
 ## [Unreleased]
+(empty — accumulates entries for the next release)
+
+## [0.1.0] - 2026-05-14

 ### Added
 - ...everything that landed since the last release
```

The release workflow's `github-release` job parses this file by exact heading match (`## [0.1.0] - ...`), so the format matters.

### 3. Update `pyproject.toml`

```diff
-version = "0.1.0.dev0"
+version = "0.1.0"
```

(Skip if `pyproject.toml` already says `0.1.0`. The post-release housekeeping step below is what introduces the `.dev0` suffix between releases.)

### 4. Commit, tag, push

```bash
git add CHANGELOG.md pyproject.toml
git commit -m "release: v0.1.0"
git tag -a v0.1.0 -m "v0.1.0"
git push origin main
git push origin v0.1.0
```

### 5. Watch the workflow

Open <https://github.com/surajit003/siphyy/actions>. The **Release** workflow runs through four jobs:

1. **validate** — checks the tag's version segment equals `pyproject.toml`'s `version`. Fails fast on mismatch.
2. **build** — `uv build` produces `dist/*.whl` and `dist/*.tar.gz`; `twine check` validates metadata.
3. **publish-pypi** — uses the `pypi` [GitHub Environment](https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment) + OIDC to upload. If you've configured a required reviewer on the environment, the job pauses for approval here.
4. **github-release** — creates `https://github.com/surajit003/siphyy/releases/tag/v0.1.0` with the changelog excerpt as the body and the wheel + sdist as downloads.

When the workflow finishes green, the release is live: `pip install siphyy==0.1.0` works.

### 6. Post-release housekeeping

Bump to the next development version so accidental local builds from `main` don't collide with the just-released artefact on PyPI:

```bash
# Edit pyproject.toml: version = "0.1.0" → "0.2.0.dev0" (or 0.1.1.dev0)
git add pyproject.toml
git commit -m "chore: bump to 0.2.0.dev0"
git push origin main
```

The `.dev0` is PEP 440 for "pre-pre-release-of-this-version" — strictly less than `0.2.0a1`, which is less than `0.2.0rc1`, which is less than `0.2.0`. PyPI orders them correctly.

## One-time PyPI setup

Before the first release ever ships, do these two things. After this, releases are fully automated.

### Set up trusted publishing on PyPI

PyPI supports [OIDC-based publishing](https://docs.pypi.org/trusted-publishers/) from GitHub Actions — no long-lived API token, scoped to a specific workflow + environment + repo.

If `siphyy` doesn't exist on PyPI yet, use the **pending publisher** flow:

1. Sign in at <https://pypi.org/manage/account/publishing/>.
2. Click **Add a new pending publisher**.
3. Fill in:
   - **PyPI Project Name**: `siphyy`
   - **Owner**: `surajit003`
   - **Repository name**: `siphyy`
   - **Workflow filename**: `release.yml`
   - **Environment name**: `pypi`
4. Save.

The first release will create the PyPI project and consume the pending publisher in one operation. There's no API token to rotate.

### Set up the GitHub Environment

1. In the repo: **Settings → Environments → New environment**.
2. Name: `pypi` (must match the publisher config above).
3. **Recommended:** under **Deployment protection rules**, add yourself as a **required reviewer**. The release workflow will pause and request approval before publishing — a deliberate "wait, is this the right tag?" moment that catches accidental tag pushes.
4. **Recommended:** restrict deployments to tags matching `v*` so only tag-triggered runs can use the environment.

## Yanking a bad release

If a release breaks something obvious for users, **yank** it on PyPI. Yanked releases stay visible (so anyone who pinned the version still works) but are skipped by `pip install` by default:

1. <https://pypi.org/manage/project/siphyy/releases/>
2. Find the version → **Yank release**
3. Provide a yank reason ("incorrect schema migration", "import error on Python 3.14.0", etc.). It's shown to anyone who tries to install.

Cut a fixed `0.1.1` immediately. Deletion is almost always the wrong call — yanking is reversible and preserves the historical record.

## Troubleshooting

**`validate` job fails: "tag doesn't match pyproject.toml".**
You forgot step 3 (update `pyproject.toml`'s version). Either bump `pyproject.toml` to match the tag and re-push the commit, or delete the tag and start over:

```bash
git tag -d v0.1.0
git push origin :v0.1.0
# fix pyproject.toml, recommit, retag
```

**`publish-pypi` fails with "no trusted publisher".**
The one-time PyPI setup wasn't done. Configure the pending publisher (see above), then re-run the failed job from the Actions tab.

**`publish-pypi` fails with "version already exists".**
The version was already published. PyPI doesn't allow republishing the same version even after yanking; cut a new version (`0.1.1`) instead.

**GitHub Release body is empty / generic.**
The `github-release` job couldn't find a matching `## [VERSION] - DATE` section in `CHANGELOG.md`. Check the heading format — exact match required: `## [0.1.0] - 2026-05-14`, not `## [v0.1.0]` or `## [0.1.0] (2026-05-14)`.

**A release fails halfway through.**
Re-run failed jobs from the Actions tab. `uv build` is deterministic; PyPI rejects duplicate version uploads (good — protects you from double-publishing); the `github-release` step is idempotent for a given tag.

**Need to test the workflow without actually publishing.**
Tag a `v0.0.0` somewhere and let it fail at `publish-pypi` (no pending publisher would match). The earlier `validate` + `build` jobs run end-to-end and surface any pyproject/build errors. Delete the tag afterward.
