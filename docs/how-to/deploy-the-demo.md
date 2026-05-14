# Deploy the demo

The Streamlit demo under `apps/demo/` visualises the pipeline end-to-end — adapter → detector → agent, with every prompt the LLM receives visible in the UI. Deployment target: HuggingFace Spaces (free, persistent, no cold-start).

## Auto-deploy from GitHub Actions (recommended)

`.github/workflows/deploy-demo.yml` is set up to push `apps/demo/*` to the HF Space on every change. One-time setup:

1. **Generate an HF access token** at <https://huggingface.co/settings/tokens>. Permission: **Write**.
2. **Add it as a GitHub secret**: in the repo, *Settings → Secrets and variables → Actions → New repository secret*. Name: `HF_TOKEN`.
3. **Create the empty HF Space** at <https://huggingface.co/new-space>. SDK: **Docker**, Hardware: **CPU basic** (Free), Visibility: **Public**. Owner / name must match the workflow's env vars (`HF_USERNAME` / `HF_SPACE`, default `surajit003/siphyy`).
4. **Push any change under `apps/demo/`** — or trigger the workflow manually from the Actions tab. First HF build takes 3–5 minutes.

Then every push to `main` that touches `apps/demo/**` redeploys.

## Manual deploy

If you'd rather not wire up CI yet:

```bash
git clone https://huggingface.co/spaces/<owner>/<space-name> hf-space
cp apps/demo/{app.py,requirements.txt,Dockerfile,README.md} hf-space/
cp -r apps/demo/data hf-space/
cd hf-space && git add . && git commit -m "deploy" && git push
```

## What HF actually runs

`apps/demo/Dockerfile` is the build recipe:

- Base: `python:3.14-slim`
- Installs `git` (needed because `requirements.txt` fetches `siphyy` from GitHub)
- Installs the demo's deps (streamlit, openai, anthropic, the library)
- Runs as a non-root user (HF requirement)
- Binds Streamlit to `0.0.0.0:7860` (HF's default exposed port)

`apps/demo/README.md`'s YAML frontmatter is how HF identifies the Space:

```yaml
sdk: docker
app_port: 7860
```

If the port doesn't line up between the Dockerfile and `app_port`, the Space shows a 504. Both are 7860 by default — change one without the other and you'll trip yourself.

## Costs and limits

The demo's UX is bring-your-own-key — users paste their own OpenAI/Anthropic key in the sidebar, your hosting cost is $0/month. If you want a "try without a key" option:

1. Add `OPENAI_API_KEY` and/or `ANTHROPIC_API_KEY` as **Space secrets** (*Settings → Variables and secrets* on the Space itself, not on GitHub).
2. Extend `_build_llm_client` in `apps/demo/app.py` to fall through to the Space-level key when the user doesn't supply one.
3. **Pair with a per-IP rate limiter before going public** — otherwise a single curious user can drain your monthly budget.

For a small public demo, this is probably overkill. Stick with BYO-key.

## Hosting elsewhere

The Dockerfile is generic — anywhere that can run a `python:3.14-slim` container on port 7860 will work. Tested patterns:

- **Streamlit Community Cloud** — drop `app.py` + `requirements.txt` into a repo, point Streamlit Cloud at it. No Dockerfile needed there. Free tier sleeps after 7 days of inactivity (cold-start ~30s).
- **Railway / Render / Fly.io** — point at `apps/demo/Dockerfile` directly. ~$5/month for always-on, no sleep.
- **Your own VPS** — `docker build apps/demo/` and `docker run -p 7860:7860 <image>`.

HF Spaces wins for OSS demos because the audience overlap is high (people browsing HF Spaces are exactly the people who'd try an AI-pipeline framework) and the cost is zero.
