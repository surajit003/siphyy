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

### One-time setup: GitHub → HF auto-deploy

The `.github/workflows/deploy-demo.yml` workflow at the repo root pushes `apps/demo/*` to the HF Space on every change. Setup is a four-step, one-time thing:

1. **Generate a HuggingFace access token** at <https://huggingface.co/settings/tokens>. Pick **Write** permission. Copy it.
2. **Add it as a GitHub secret** in this repo: *Settings → Secrets and variables → Actions → New repository secret*. Name it exactly `HF_TOKEN`.
3. **Create the empty HF Space** at <https://huggingface.co/new-space>. SDK = **Docker**, Hardware = **CPU basic** (Free), Visibility = **Public**. Owner / name must match what the workflow expects (defaults to `surajit003/siphyy` — edit the `HF_USERNAME` / `HF_SPACE` env vars in the workflow if different).
4. **Push any change under `apps/demo/`** (or trigger the workflow manually from the Actions tab). The workflow clones the Space repo, copies the demo files in, and pushes back. First build on HF takes 3–5 minutes (Docker fresh-build of Python 3.14 + Streamlit); subsequent builds are layer-cached.

After that, every push to `main` that touches `apps/demo/**` redeploys automatically. URL: `https://huggingface.co/spaces/<owner>/<space>`.

### Manual / first-deploy path

If you'd rather bootstrap once by hand (e.g. before CI is configured):

```bash
git clone https://huggingface.co/spaces/<owner>/<space> hf-siphyy
cp apps/demo/{app.py,requirements.txt,Dockerfile,README.md} hf-siphyy/
cd hf-siphyy && git add . && git commit -m "initial deploy" && git push
```

### Optional: house API key for rate-limited public demo

The app's default UX is bring-your-own-key. If you want a "try without a key" path, add `OPENAI_API_KEY` and/or `ANTHROPIC_API_KEY` as **Space secrets** (*Settings → Variables and secrets* on the Space, not GitHub) and extend `_build_llm_client` in `app.py` to fall through to those when the user leaves the key field blank. Pair with per-session rate limiting before going public, or your token gets drained.

## Privacy posture

- Uploaded files are processed in memory only — never written to disk or logged.
- API keys live in the user's browser session only.
- The selected LLM provider receives the canonical events and historical cases as part of the prompt. The **Mock** option lets users see the flow without sending anything to a real LLM.
- Upload size capped at 2 MB to keep the demo focused on small samples.

## License

Apache-2.0, same as the library.
