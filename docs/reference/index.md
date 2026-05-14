# API reference

Auto-generated from docstrings via [mkdocstrings](https://mkdocstrings.github.io/). Every signature, every field description here is rendered from the actual source — there's no second copy to keep in sync.

If something in the rendered docs disagrees with the codebase, the codebase is the ground truth. File an issue.

## Modules

- **[Schema](schema.md)** — canonical event types (`TelemetryReading`, `DriverEvent`, `InterestingEvent`), case base types, sensor type literals.
- **[Adapters](adapters.md)** — `TelematicsAdapter` ABC + `TrakzeeAdapter`.
- **[Detectors](detectors.md)** — `Detector` ABC, `StateStore` Protocol, `InMemoryStateStore`, `FuelSiphonageDetector`.
- **[Agents](agents.md)** — `Agent` ABC, `LLMClient` Protocol, `OpenAILLMClient`, `AnthropicLLMClient`, `MockLLMClient`, `FuelAnomalyAgent`, `FuelAnomalyReport`.

## Conventions

- Fields with no default are required.
- Fields with `... | None = None` are optional and default to `None`.
- Enums are `typing.Literal[...]` — easier to grep than `enum.Enum`.
- All models are frozen and forbid extras. Constructing one with an unknown field raises `ValidationError`.
