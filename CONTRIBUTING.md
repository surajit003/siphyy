# Contributing to Siphyy

Thanks for your interest. This project is Apache-2.0 licensed and welcomes contributions from anyone.

## Setting up a development environment

```bash
git clone https://github.com/siphyy/siphyy-core.git
cd siphyy-core

# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install in editable mode with all dev dependencies
uv venv
source .venv/bin/activate
uv pip install -e ".[dev,trakzee,llm,storage]"

# Set up pre-commit hooks (runs lint + format on commit)
pre-commit install
```

## Running tests

```bash
pytest                          # full suite with coverage
pytest tests/test_canonical_schema.py   # one file
pytest -k trakzee               # by keyword
pytest --no-cov                 # skip coverage (faster iteration)
```

## Style

- Code style is enforced by `ruff` and `mypy`. Just run `pre-commit run --all-files` before pushing.
- Type-hint every function signature. We aim for `strict` mypy compliance.
- Public APIs need docstrings; internal helpers can skip them.
- Test every adapter against at least one realistic provider payload fixture.
- Prefer explicit over clever. This is infrastructure code people will read.

## Documentation

The full docs site lives under `docs/` and is built with [MkDocs + Material](https://squidfunk.github.io/mkdocs-material/). Preview locally:

```bash
uv pip install -e ".[docs]"
mkdocs serve                    # http://localhost:8000
```

The site auto-reloads on save. `mkdocs build --strict` is what CI runs — same command, fails on broken links or missing pages.

When you add a new module under `src/siphyy/`, the API reference picks it up automatically via `mkdocstrings` if you add a one-liner to `docs/reference/<area>.md`:

```markdown
::: siphyy.your_new_module
```

Conceptual docs (the *why*) live under `docs/concepts/`; recipe-style answers (the *how*) under `docs/how-to/`; the progressive learning path under `docs/tutorial/`. The README's quickstart links into the tutorial; keep the two in sync if you change either.

## Writing an adapter for a new telematics provider

1. Create `src/siphyy/adapters/yourprovider.py`.
2. Subclass `TelematicsAdapter` and implement `adapt()`.
3. Set `name` to your provider identifier (lowercase, no spaces).
4. Convert all units to canonical: km, km/h, Celsius, UTC.
5. Add a sample provider payload to `tests/fixtures/`.
6. Write tests in `tests/test_yourprovider_adapter.py`.
7. Add an optional install group to `pyproject.toml` if your adapter needs extra deps.
8. Update the README's "Supported providers" section.

## Contributor License Agreement

By submitting a pull request, you agree that:

1. Your contribution is your original work (or you have rights to submit it).
2. You grant the project maintainer a license to use, modify, redistribute, and **relicense** your contribution under any OSI-approved license, including dual-licensing for commercial purposes.

This CLA exists so the project can adapt its license in the future if needed (e.g., adopting BSL for newer major versions while keeping older versions under Apache 2.0). The first time you open a PR, our CLA bot will ask you to sign. It's a one-time, click-through process.

## Code of Conduct

Be kind. Disagree about ideas, never about people. Anything else gets you removed. Full text in [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Releasing (maintainers)

Releases are cut by pushing a `v*` tag — the GitHub Actions workflow builds, publishes to PyPI via OIDC trusted publishing, and creates the GitHub Release. The full maintainer playbook (including versioning rules during alpha, the one-time PyPI trusted-publisher setup, and yanking) lives at [docs/about/releasing.md](docs/about/releasing.md).

## What to work on

- Open issues labeled `good first issue` are designed for newcomers.
- New adapters are almost always welcome — see the list of unsupported providers in the README.
- Improvements to docs, examples, and test coverage are always valuable.
- Major architectural changes — open an issue first to discuss before sending a PR.

## Questions?

Open a GitHub Discussion. Don't email maintainers privately for technical questions — public answers help future contributors too.
