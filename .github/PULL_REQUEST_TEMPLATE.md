<!--
Thanks for sending a PR. Filling this out makes review faster and the
merge less likely to bounce on CI. None of the boxes are mandatory but
the ones that apply to your change should be ticked.
-->

## What does this PR do?

<!-- One paragraph: what changes, what the user-facing effect is. -->

## Why?

<!-- The motivation. Link to issues, the design doc, or prior
     discussion where relevant. -->

Closes #

## How is this tested?

- [ ] New unit tests cover the changed code paths
- [ ] Existing tests still pass (`uv run pytest`)
- [ ] Ran `ruff check`, `ruff format --check`, and `mypy src` locally
- [ ] If docs changed: `mkdocs build --strict` succeeds

## Architectural checklist

<!-- Tick only the boxes that apply to your change. -->

- [ ] If this changes the canonical schema: `schema_version` bumped (breaking)
      *or* only optional fields added (non-breaking)
- [ ] If this adds a new adapter: exercised against a realistic provider payload
      under `tests/`
- [ ] If this adds a new detector: tested against both firing and non-firing
      scenarios, plus a no-fuel-data / wrong-event-type / missing-state
      sanity case
- [ ] If this adds a new `LLMClient` implementation: covered by both unit
      tests (stubbed) and an integration test under `tests/integration/`
      gated on the relevant API-key env var
- [ ] If this adds a new physical-cause false-positive vector: paired with a
      seed case in `siphyy.knowledge.seed_cases` so the agent learns the
      pattern

## What's left out, and why?

<!-- Anything you considered including but decided to defer. Helps
     reviewers understand the scope intent. -->

## Screenshots / output

<!-- For UI changes (the Streamlit demo) or behaviour changes (new
     detector output, new report shape), paste a screenshot or the
     relevant before/after output. -->
