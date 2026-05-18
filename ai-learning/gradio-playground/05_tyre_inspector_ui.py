"""
Demo 5: Tyre Inspector with Gradio UI

Wraps `fleet_ops/tyre_inspector.py` behind a web UI. Upload a tyre photo
and watch:
  - GPT-5 analyse it (left pane)
  - Claude Opus 4.7 analyse it (right pane)
  - GPT audit Claude's assessment (lower left)
  - Claude audit GPT's assessment (lower right)

Four parallel API calls. Total wall-clock: ~5-10 seconds.

Run with:
    cd /Users/surajitdas/Downloads/siphyy-core/ai-learning
    ./.venv/bin/python gradio-playground/05_tyre_inspector_ui.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import gradio as gr

# Make fleet_ops importable. tyre_inspector loads its own .env from there.
FLEET_OPS_DIR = Path(__file__).parent.parent / "fleet_ops"
sys.path.insert(0, str(FLEET_OPS_DIR))

from tyre_inspector import (  # noqa: E402  (after sys.path edit)
    analyze_in_parallel,
    cross_evaluate_in_parallel,
)


def run_full_pipeline(image_path: str | None) -> tuple[dict, dict, dict, dict]:
    """Run both vendor analyses + both cross-evaluations on the uploaded image.

    Returns four dicts (for Gradio JSON display):
        (gpt_assessment, claude_assessment, gpt_eval_of_claude, claude_eval_of_gpt)
    """
    if not image_path:
        empty = {"error": "Upload an image first."}
        return empty, empty, empty, empty

    path = Path(image_path)

    # Phase 1: both vendors analyse the same image in parallel.
    gpt_result, claude_result = analyze_in_parallel(path)

    # Phase 2: each model audits the other's assessment, in parallel.
    gpt_eval, claude_eval = cross_evaluate_in_parallel(path, gpt_result, claude_result)

    return (
        gpt_result.model_dump(),
        claude_result.model_dump(),
        gpt_eval.model_dump(),
        claude_eval.model_dump(),
    )


with gr.Blocks(title="Tyre Inspector — Vendor Comparison") as demo:
    gr.Markdown(
        "# Tyre Inspector\n\n"
        "Upload a tyre photo. Two vision models analyse it independently, "
        "then each audits the other's assessment.\n\n"
        "**4 API calls per click, all parallel. ~5-10 seconds total.**"
    )

    image_input = gr.Image(type="filepath", label="Upload tyre photo")
    analyze_btn = gr.Button("Run full pipeline", variant="primary")

    gr.Markdown("## Vendor assessments")
    with gr.Row():
        gpt_output = gr.JSON(label="GPT-5 says")
        claude_output = gr.JSON(label="Claude Opus 4.7 says")

    gr.Markdown("## Cross-evaluation — LLM-as-a-judge")
    with gr.Row():
        gpt_eval_output = gr.JSON(label="GPT's evaluation of Claude")
        claude_eval_output = gr.JSON(label="Claude's evaluation of GPT")

    analyze_btn.click(
        fn=run_full_pipeline,
        inputs=image_input,
        outputs=[gpt_output, claude_output, gpt_eval_output, claude_eval_output],
    )


if __name__ == "__main__":
    demo.launch()
