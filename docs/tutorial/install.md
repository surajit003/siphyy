# Install

Siphyy targets Python 3.14+. The recommended setup uses [`uv`](https://docs.astral.sh/uv/) for environment management.

## Prerequisites

- **Python 3.14** or newer. Older Pythons aren't supported; the framework leans on modern type-parameter syntax (`def complete[T: BaseModel](...)`) that landed in 3.12+, and the canonical event schema uses fields introduced after 3.13.
- **`uv`** — fastest way to get a reproducible Python environment. Install with `curl -LsSf https://astral.sh/uv/install.sh | sh` (macOS/Linux) or `winget install --id=astral-sh.uv` (Windows).
- **An LLM API key** (optional for Tier 1, required for Tier 2) — OpenAI or Anthropic. Or skip and use `MockLLMClient`.

## Clone and set up the development environment

```bash
git clone https://github.com/surajit003/siphyy.git
cd siphyy
uv sync                              # creates .venv, installs everything
```

`uv sync` reads `pyproject.toml`, creates a `.venv/`, and installs the library plus all optional extras declared as default dependency groups (currently just `[dev]`). To pull in the Trakzee adapter, LLM clients, and the Streamlit demo, install the extras explicitly:

```bash
uv pip install -e ".[dev,trakzee,llm,demo]"
```

Available extras:

| Extras | What it adds |
|---|---|
| `dev` | `pytest`, `ruff`, `mypy`, `pre-commit`, `pytest-cov`, `python-dotenv` |
| `trakzee` | `pandas`, `openpyxl` — needed to read `.xlsx` exports |
| `llm` | `openai`, `anthropic` — the two reference LLM client implementations |
| `storage` | `psycopg`, `sqlalchemy` — pgvector-backed case base (planned) |
| `demo` | `streamlit` — the visualiser app under `apps/demo/` |
| `docs` | `mkdocs-material`, `mkdocstrings` — what built the site you're reading |

## Install from PyPI

Once a release is cut:

```bash
pip install "siphyy[trakzee,llm]"
# or
uv pip install "siphyy[trakzee,llm]"
```

## Verify

```bash
uv run python -c "import siphyy; print(siphyy.__version__)"
```

You should see the current version printed. If you get `ModuleNotFoundError`, the extras install didn't take — re-run `uv sync` from the repo root and try again.

## API keys (optional)

Drop a `.env` file at the repo root with the keys you have:

```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

The quickstart, the test suite (for integration tests), and the demo app all soft-load `.env` automatically. Without keys, everything still works via `MockLLMClient`.

Next: [run your first pipeline →](first-pipeline.md)
