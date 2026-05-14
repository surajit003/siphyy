---
title: Siphyy Demo
emoji: ⛽
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
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

HF retired their managed Streamlit SDK; Spaces now hosts non-Gradio apps via Docker. The `Dockerfile` in this directory + the YAML frontmatter at the top of this README is the full deployment config.

**Standalone Space (recommended for first deploy)**

1. Create a new Space at <https://huggingface.co/new-space>. Pick **Docker** as the SDK, **CPU basic** as the hardware, public visibility.
2. Clone the empty Space repo locally:
   ```bash
   git clone https://huggingface.co/spaces/<your-username>/<space-name> hf-siphyy
   ```
3. Copy the contents of `apps/demo/` into the Space repo root:
   ```bash
   cp apps/demo/app.py apps/demo/requirements.txt apps/demo/Dockerfile apps/demo/README.md hf-siphyy/
   ```
4. Push to HF:
   ```bash
   cd hf-siphyy && git add . && git commit -m "initial deploy" && git push
   ```

First build takes ~3-5 minutes (the Dockerfile compiles deps fresh). HF then serves the app at `https://huggingface.co/spaces/<your-username>/<space-name>`.

**Linked-repo (auto-deploy on `git push` to GitHub)**

After your first standalone deploy, you can link a GitHub repo as a remote source under the Space's *Settings → Linked git repository*. Subsequent pushes to GitHub `main` redeploy automatically. The Space still uses the same Dockerfile / requirements.txt — only the source of truth changes.

For both paths, API keys are *not* needed at the Space level — the app uses a bring-your-own-key UX. If you want to offer a rate-limited demo key, add `OPENAI_API_KEY` (and/or `ANTHROPIC_API_KEY`) as a Space secret under *Settings → Variables and secrets* and extend `_build_llm_client` to fall through to it.

## Privacy posture

- Uploaded files are processed in memory only — never written to disk or logged.
- API keys live in the user's browser session only.
- The selected LLM provider receives the canonical events and historical cases as part of the prompt. The **Mock** option lets users see the flow without sending anything to a real LLM.
- Upload size capped at 2 MB to keep the demo focused on small samples.

## License

Apache-2.0, same as the library.
