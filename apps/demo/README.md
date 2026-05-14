---
title: Siphyy Demo
emoji: ⛽
colorFrom: blue
colorTo: indigo
sdk: streamlit
sdk_version: "1.30.0"
app_file: app.py
pinned: false
license: apache-2.0
short_description: Provider-agnostic fleet telematics pipeline — schema → adapter → Tier 1 detector → Tier 2 LLM agent, visualised step by step.
---

# Siphyy — fleet telematics demo

This Streamlit app is the live demo for [`siphyy-core`](https://github.com/surajit003/siphyy). It loads a small Trakzee-shaped sample (or a file you upload), runs it through the full pipeline — canonical schema, Tier 1 rule-based detector, Tier 2 LLM-grounded agent — and shows every step, including the exact prompt sent to the LLM.

## What you'll see

1. **Adapter** — provider rows become canonical `TelemetryReading` events.
2. **Tier 1 detector** — `FuelSiphonageDetector` flags candidates for review.
3. **Tier 2 agent** — `FuelAnomalyAgent` retrieves historical cases, builds a grounded prompt, calls the LLM, and produces a structured `FuelAnomalyReport`.
4. **Reports** — final verdicts with confidence, reasoning, and recommended actions.

The bundled sample is engineered to demonstrate both outcomes the framework is designed to handle:

- **SAMPLE-001** — an injected siphonage event (47 % fuel drop in 18 min, engine off). The agent should rule `likely_siphonage`.
- **SAMPLE-002** — a slope-effect false positive (18 % drop in 7 min, after a 95 m climb). The agent should rule `likely_false_positive`.

## Running locally

From the repo root:

```bash
uv sync --extra demo --extra trakzee --extra llm
uv run streamlit run apps/demo/app.py
```

The app opens at <http://localhost:8501>. Drop an `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` into the sidebar, or pick the **Mock** option to see the full flow with realistic canned verdicts (no key needed).

## Deploying to HuggingFace Spaces

The YAML frontmatter at the top of this README is the Space configuration HuggingFace reads — Spaces auto-detects `sdk: streamlit` and runs `app_file: app.py`. Two deployment paths:

**Linked-repo (recommended)**
1. Create a new Space on HuggingFace: <https://huggingface.co/new-space>, choose **Streamlit** as the SDK.
2. Under "Files & versions" → "Add a remote git repo as a source", point at this GitHub repo and set the **subdirectory** to `apps/demo/`.
3. The Space rebuilds automatically on every push to `main`.

**Standalone Space**
1. Create the Space and clone its git repo locally.
2. Copy the contents of `apps/demo/` into the Space repo root.
3. Push. The Space builds via `requirements.txt`, which pulls `siphyy` from this GitHub repo's `main`.

For both paths, API keys are *not* needed at the Space level — the app uses a bring-your-own-key UX. If you want to offer a rate-limited demo key, add `OPENAI_API_KEY` (and/or `ANTHROPIC_API_KEY`) as a Space secret and extend `_build_llm_client` to fall through to it.

## Privacy posture

- Uploaded files are processed in memory only — never written to disk or logged.
- API keys live in the user's browser session only.
- The selected LLM provider receives the canonical events and historical cases as part of the prompt. The **Mock** option lets users see the flow without sending anything to a real LLM.
- Upload size capped at 2 MB to keep the demo focused on small samples.

## License

Apache-2.0, same as the library.
