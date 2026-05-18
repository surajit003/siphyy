# Gradio Playground

A sandbox for learning the three core Gradio patterns, each wired to a real OpenAI call.

| File | Pattern | What it does |
|---|---|---|
| `01_images.py` | Image input + vision API | Drop a photo → GPT-4o-mini describes it |
| `02_streaming.py` | Streaming with `yield` + `stream=True` | Watch the answer assemble token-by-token |
| `03_maps.py` | Structured outputs + folium + `gr.HTML` | Plain-English place query → real map with pins |
| `04_combined.py` | All three in one tabbed dashboard | The "production-feel" version |

## Setup

You're already set up if the parent `ai-learning/.venv` was built. It has `gradio`, `folium`, `openai`, `pydantic`, `python-dotenv`.

The OpenAI key is loaded from `siphyy-core/.env` automatically.

## Run

Each file is standalone — runs its own Gradio server on localhost.

```bash
cd /Users/surajitdas/Downloads/siphyy-core/ai-learning
./.venv/bin/python gradio-playground/01_images.py
```

The terminal prints a URL like `http://127.0.0.1:7860`. Open it in your browser.

**Ctrl+C in the terminal stops the server.**

## Try this

### `01_images.py`
- Drop in one of your fleet tyre photos (`fleet_ops/punctured_tyre.png`)
- A screenshot of your code
- A meme — see if GPT recognises it
- A whiteboard photo of notes

### `02_streaming.py`
- *"Write a haiku about Nairobi traffic"*
- *"Explain MCP servers in one sentence"*
- *"What are the top 3 things to know about Kenyan logistics?"*
- Try a long question — watch the response stream for several seconds

### `03_maps.py`
- *"Major ports in East Africa"*
- *"Top 5 universities in Kenya"*
- *"Capitals of South American countries"*
- *"Highest mountains in the world"*

### `04_combined.py`
- All three tabs in one browser window — switch between them
- This is the layout shape a real product would use (tabs grouping related features)

## What you're learning

| Pattern | The trick |
|---|---|
| **Image** | Encode the picture to base64, send it as a `data:image/png;base64,...` URL to the vision API |
| **Streaming** | Replace `return` with `yield`. Set `stream=True` on the OpenAI call. Yield the cumulative answer on each chunk. |
| **Map** | Use `pydantic` + `client.chat.completions.parse()` for typed `(name, lat, lon)` output. Pass to folium. Return `m._repr_html_()` to `gr.HTML`. |

## Troubleshooting

| Symptom | Fix |
|---|---|
| `OSError: Cannot find empty port in range` | Previous demo still running on port 7860. Ctrl+C it, or use `gr.close_all()` in a Python REPL. |
| `Authentication error` | `OPENAI_API_KEY` not loaded. Check `siphyy-core/.env` exists and has the key. |
| Map doesn't show | Missed the `_repr_html_()` call on the folium map. |
| Streaming dumps the full answer at once | You used `return` instead of `yield`, or forgot `stream=True`. |

## What's next

When all four demos run, the natural extension is to:

1. **Wire your tyre inspector to a Gradio UI** — replace `01_images.py`'s `analyze_image` body with a call to your `tyre_inspector.analyze_with_openai`. You'd have a fully-functional fleet tyre safety web app in ~15 minutes.
2. **Add `share=True`** to any `demo.launch()` to get a temporary public URL — useful for showing demos to non-technical people.
3. **Combine streaming + image** — upload a tyre image, watch the LLM stream out its assessment paragraph by paragraph. Great UX.

These three patterns + your existing MCP/RAG knowledge = the full toolkit for "AI demo apps" in 2026.
