---
name: Bug report
about: Something isn't working as expected
title: ''
labels: bug
assignees: ''
---

## Summary

<!-- One sentence: what's broken. -->

## Steps to reproduce

<!-- The smallest sequence that triggers the bug. Paste code if helpful. -->

1.
2.
3.

## Expected behaviour

<!-- What you thought would happen. -->

## Actual behaviour

<!-- What actually happened. Paste the full traceback / error inside the
     code block below. -->

```
<paste traceback / error output here>
```

## Environment

<!-- Run the commands; paste the output. -->

- siphyy version: `python -c "import siphyy; print(siphyy.__version__)"`
- Python version: `python --version`
- OS: macOS / Linux / Windows
- Installation method: `uv sync` / `pip install`
- Relevant extras installed: `[trakzee]` / `[llm]` / `[demo]` / `[dev]` / …

## Does it reproduce against the bundled sample data?

<!-- The quickstart (`uv run python examples/quickstart.py`) runs against
     anonymised sample data. If the bug reproduces there too, mention it —
     it makes triage much faster. -->

- [ ] Yes, reproduces against `apps/demo/data/sample_trakzee.json`
- [ ] No, only reproduces with my own data
- [ ] N/A — not a data-processing bug

## Additional context

<!-- Anything else useful: provider you're adapting, LLM client in use,
     whether you've tried recent main, screenshots, etc. -->
