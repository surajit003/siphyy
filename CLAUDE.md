# Guidance for AI coding assistants

This file orients an LLM (Claude Code, Cursor, etc.) working on this repo. It complements `CONTRIBUTING.md`.

## What this project is

Open-source agentic framework for fleet telematics. Provider-agnostic canonical schema, cheap Tier 1 detectors, LLM-grounded Tier 2 agent, optional curated Knowledge Pack for paying customers.

## Architectural rules that matter

1. **The canonical schema is the contract.** Everything past the adapter layer reasons in `TelemetryReading` / `DriverEvent`, never in raw provider dicts. Don't add provider-specific fields to canonical types — use `provider_extras`.

2. **Adapters are pure.** No network calls, no DB writes, no shared state. They translate dicts into canonical events. Side effects belong elsewhere.

3. **Missing data is `None`, never fabricated.** If a provider doesn't expose RPM, the canonical field is `None`. Detectors handle `None` gracefully.

4. **Units are canonical.** km, km/h, Celsius, UTC. Adapters convert at the boundary. Downstream code never thinks about miles or local time.

5. **Tier 1 ≠ Tier 2.** Tier 1 is rule-based, cheap, deterministic. Tier 2 is LLM-based, expensive, used selectively. If you're tempted to make Tier 1 "smarter" by adding LLM calls, stop — that's what Tier 2 is for.

6. **The OSS framework does not ship customer data.** Real cases live in the proprietary Knowledge Pack. The `SEED_CASES` here are synthetic.

## Code conventions

- Python 3.14+ — use modern syntax (`X | Y`, `list[X]`, `datetime.UTC`).
- Type-hint every function signature. `from __future__ import annotations` at the top of every module.
- Pydantic models for all schemas. `ConfigDict(extra="forbid")` so typos are caught.
- Use `pathlib.Path`, not `os.path`.
- Tests live in `tests/`, mirror the `src/siphyy/` structure.
- Run `pre-commit run --all-files` before committing.

## What to avoid

- **Don't** introduce a new dependency without checking it's worth the maintenance cost. The framework has a small dep footprint on purpose.
- **Don't** add LLM API calls to Tier 1 code paths.
- **Don't** assume a single global timezone — adapters carry their own `source_timezone`.
- **Don't** widen exception handlers (`except Exception`). Catch what you can handle; let the rest crash.
- **Don't** silently drop bad data without logging it.

## How to add an adapter

1. `src/siphyy/adapters/yourprovider.py` — subclass `TelematicsAdapter`.
2. Convert units, timezones, and ID schemes inside the adapter.
3. Add a realistic sample row to `tests/conftest.py` as a fixture.
4. Mirror the `TestTrakzeeAdapter` test class — exercise valid rows, missing data, type coercion edge cases.
5. Document any provider quirks at the top of the module — they will bite future maintainers.

## How to add a detector

1. `src/siphyy/detectors/your_detector.py` — subclass `Detector` (TODO: write the base class).
2. Maintain state per-vehicle in memory (Redis-backed in production — abstract this through a `StateStore` interface).
3. Emit `InterestingEvent` objects when rules fire.
4. Detectors should be cheap. If a rule needs the LLM, it's a Tier 2 concern.

## Useful commands

```bash
pytest                                # run all tests
pytest -k fuel                        # run tests matching "fuel"
ruff check . --fix && ruff format .   # lint + format
mypy src                              # type-check
pre-commit run --all-files            # everything
```
