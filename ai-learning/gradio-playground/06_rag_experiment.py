"""
Demo 6: RAG-grounded vs baseline tyre inspection — the experiment

Upload a tyre photo. The script runs TWO analyses side by side:

  1. BASELINE: GPT sees only the image (same as 05_tyre_inspector_ui.py)
  2. GROUNDED: GPT sees the image PLUS top-K retrieved documents from
     fleet-knowledge-mcp/knowledge_base/ (tyre procedures, postmortems, etc.)

Both use the same TyreCondition schema. The only thing that changes is
the system prompt's contextual content. Compare the two outputs to see
what RAG grounding actually changes — typically more specific issues,
citations of procedure, and policy-aware recommendations.

At startup the script embeds the entire KB. This takes ~5-10s; subsequent
runs use the in-memory index.

Run with:
    cd /Users/surajitdas/Downloads/siphyy-core/ai-learning
    ./.venv/bin/python gradio-playground/06_rag_experiment.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import cast

import gradio as gr
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).parent.parent / ".env")
load_dotenv(Path(__file__).parent.parent.parent / ".env")

# Reuse tyre_inspector's schema, prompt, model, and helpers
FLEET_OPS_DIR = Path(__file__).parent.parent / "fleet_ops"
sys.path.insert(0, str(FLEET_OPS_DIR))
from tyre_inspector import (  # noqa: E402
    OPENAI_MODEL,
    SYSTEM_PROMPT,
    TyreCondition,
    load_image_as_base64,
    media_type_for,
)

client = OpenAI()

KB_DIR = Path(__file__).parent / "kb"
EMBED_MODEL = "text-embedding-3-small"
TOP_K = 2
RETRIEVAL_QUERY = "tyre condition wear damage sidewall tread inspection safety"


# ─── Tiny RAG: embed all docs at startup, cosine-sim at query time ───


def _embed(text: str) -> list[float]:
    r = client.embeddings.create(model=EMBED_MODEL, input=text)
    return r.data[0].embedding


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


print(f"Loading knowledge base from {KB_DIR.name}/ ...")
KB: list[dict] = []
for md_path in sorted(KB_DIR.glob("*.md")):
    text = md_path.read_text()
    KB.append({"source": md_path.name, "text": text, "embedding": _embed(text)})
print(f"Indexed {len(KB)} documents.\n")


def retrieve(query: str, k: int = TOP_K) -> list[dict]:
    """Return the top-k docs by cosine similarity to the query."""
    qvec = _embed(query)
    scored = [(_cosine(qvec, d["embedding"]), d) for d in KB]
    scored.sort(reverse=True, key=lambda x: x[0])
    return [
        {
            "source": d["source"],
            "similarity": round(s, 3),
            "excerpt": d["text"][:400] + ("..." if len(d["text"]) > 400 else ""),
            "full_text": d["text"],
        }
        for s, d in scored[:k]
    ]


# ─── Two analysis variants ───────────────────────────────────────────


def _build_image_message(b64: str, media_type: str) -> dict:
    return {
        "type": "image_url",
        "image_url": {"url": f"data:{media_type};base64,{b64}"},
    }


def analyze_baseline(image_path: Path) -> TyreCondition:
    """Standard analysis — no extra context, model sees only the image."""
    b64 = load_image_as_base64(image_path)
    response = client.chat.completions.parse(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Analyze this tyre image."},
                    _build_image_message(b64, media_type_for(image_path)),
                ],
            },
        ],
        response_format=TyreCondition,
    )
    return cast(TyreCondition, response.choices[0].message.parsed)


def analyze_grounded(image_path: Path, retrieved_docs: list[dict]) -> TyreCondition:
    """RAG analysis — retrieved KB docs appended to the system prompt."""
    b64 = load_image_as_base64(image_path)
    context = "\n\n## RELEVANT REFERENCE DOCUMENTS (from fleet KB):\n\n"
    for doc in retrieved_docs:
        context += f"### {doc['source']}\n{doc['full_text']}\n\n"
    grounded_system = (
        SYSTEM_PROMPT
        + context
        + "\nGround your assessment in these reference documents where applicable. "
        "Reference specific procedures or postmortems in the visible_issues or "
        "summary_for_ops_director fields when they apply."
    )
    response = client.chat.completions.parse(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": grounded_system},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Analyze this tyre image."},
                    _build_image_message(b64, media_type_for(image_path)),
                ],
            },
        ],
        response_format=TyreCondition,
    )
    return cast(TyreCondition, response.choices[0].message.parsed)


# ─── Pipeline ────────────────────────────────────────────────────────


def run_experiment(image_path: str | None) -> tuple[dict, dict, list]:
    """Run baseline + grounded analyses, return both + the retrieved docs."""
    if not image_path:
        empty = {"error": "Upload an image first."}
        return empty, empty, []

    path = Path(image_path)
    retrieved = retrieve(RETRIEVAL_QUERY, k=TOP_K)
    baseline = analyze_baseline(path)
    grounded = analyze_grounded(path, retrieved)

    # Strip the full_text from the displayed retrieval — keep the excerpt only
    displayed_retrieval = [{k: v for k, v in doc.items() if k != "full_text"} for doc in retrieved]

    return baseline.model_dump(), grounded.model_dump(), displayed_retrieval


# ─── UI ──────────────────────────────────────────────────────────────


with gr.Blocks(title="RAG Experiment — Tyre Inspector") as demo:
    gr.Markdown(
        "# RAG vs Baseline — Tyre Inspector\n\n"
        "Upload a tyre photo. Run **two analyses side by side**:\n\n"
        "- **Baseline**: GPT sees only the image\n"
        "- **Grounded**: GPT sees the image **plus** retrieved tyre procedures "
        "and postmortems from the fleet knowledge base\n\n"
        "Same model, same image, same schema. Only the context differs. "
        "Compare the responses to see what grounding actually changes."
    )

    image_input = gr.Image(type="filepath", label="Upload tyre photo")
    run_btn = gr.Button("Run experiment", variant="primary")

    gr.Markdown("## Side-by-side comparison")
    with gr.Row():
        baseline_output = gr.JSON(label="WITHOUT RAG — baseline")
        grounded_output = gr.JSON(label="WITH RAG — grounded in KB")

    gr.Markdown(
        "## What got retrieved\n\n"
        "The top-K documents the grounded version saw as context. "
        "Similarity is cosine similarity between the document's embedding and "
        "the retrieval query embedding."
    )
    retrieved_output = gr.JSON(label="Retrieved documents")

    run_btn.click(
        fn=run_experiment,
        inputs=image_input,
        outputs=[baseline_output, grounded_output, retrieved_output],
    )


if __name__ == "__main__":
    demo.launch()
