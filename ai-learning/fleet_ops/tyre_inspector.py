"""
Tyre Inspector — vision-LLM vendor comparison with cross-evaluation.

Scenario: a driver submits a tyre photo via the fleet app. The image is
analyzed by TWO vision models in parallel (GPT and Claude Opus). Each
model then evaluates the OTHER's assessment. The fleet operations director
receives both reports plus the cross-critique — catching what either
model alone might miss.
"""

from __future__ import annotations

import base64
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Literal, cast

from anthropic import Anthropic
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

# ─── Setup ───────────────────────────────────────────────────────────────

load_dotenv(Path(__file__).parent / ".env")
load_dotenv(Path(__file__).parent.parent / ".env")
load_dotenv(Path(__file__).parent.parent.parent / ".env")

openai_client = OpenAI()
anthropic_client = Anthropic()

OPENAI_MODEL = "gpt-5"
ANTHROPIC_MODEL = "claude-opus-4-7"


# ─── Schemas ─────────────────────────────────────────────────────────────


class TyreCondition(BaseModel):
    """Structured tyre condition assessment, returned by either vision model."""

    tread_depth_estimate_mm: float = Field(
        ge=0,
        le=10,
        description="Estimated remaining tread depth in mm. Legal minimum is 1.6mm.",
    )
    overall_condition: Literal["new", "good", "fair", "worn", "dangerous"] = Field(
        description="One-word overall classification."
    )
    safety_score: int = Field(
        ge=1,
        le=10,
        description="Safety score 1-10. 10 = brand new, 1 = remove from service NOW.",
    )
    visible_issues: list[str] = Field(
        default_factory=list,
        description="Specific defects observed in the image.",
    )
    recommended_action: Literal[
        "continue_use",
        "schedule_replacement",
        "replace_immediately",
        "remove_from_service",
    ] = Field(description="What the ops director should DO based on this assessment.")
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence 0-1. Lower for unclear or partial images.",
    )
    summary_for_ops_director: str = Field(
        description="2-3 sentence plain-English summary for the ops director."
    )


class CrossEvaluation(BaseModel):
    """One model's evaluation of another model's TyreCondition output."""

    accuracy_score: int = Field(
        ge=1,
        le=10,
        description="How accurate is the other model's assessment (1-10)?",
    )
    thoroughness_score: int = Field(
        ge=1,
        le=10,
        description="Did the other model catch all visible issues (1-10)?",
    )
    overconfident: bool = Field(description="Is the other model's confidence inappropriately high?")
    underconfident: bool = Field(description="Is the other model's confidence inappropriately low?")
    things_missed: list[str] = Field(
        default_factory=list,
        description="Issues the other model failed to flag.",
    )
    things_overstated: list[str] = Field(
        default_factory=list,
        description="Issues the other model exaggerated or imagined.",
    )
    overall_quality: Literal["excellent", "good", "adequate", "poor"]
    rationale: str = Field(description="Brief explanation of these scores.")


# ─── Prompts ─────────────────────────────────────────────────────────────


SYSTEM_PROMPT = """\
You are a commercial vehicle tyre safety inspector with 20 years of \
experience in fleet operations. You analyze tyre photographs submitted by \
drivers and produce structured safety assessments for the fleet operations \
director.

When analyzing a tyre image, focus on:
- Tread depth (estimate in mm; legal minimum is 1.6mm in most regions)
- Tread wear pattern (uneven wear indicates alignment or pressure issues)
- Sidewall condition (cracks, bulges, cuts, cord exposure)
- Overall structural integrity (any visible signs of impending failure)
- Foreign objects (embedded nails, screws, debris)

Be honest, conservative on safety, specific, and actionable. If the image \
is unclear, lower the confidence score and note the limitation."""


CROSS_EVAL_PROMPT = """\
You are auditing another vision model's tyre assessment for the same image. \
Examine the image yourself, then evaluate the other model's report. Identify \
issues it missed, issues it overstated, and whether its confidence is \
appropriately calibrated. Be specific and grounded in what's actually visible."""


# ─── Helpers ─────────────────────────────────────────────────────────────


def load_image_as_base64(image_path: Path) -> str:
    return base64.standard_b64encode(image_path.read_bytes()).decode("utf-8")


def media_type_for(image_path: Path) -> str:
    ext = image_path.suffix.lower().lstrip(".")
    return {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "webp": "image/webp",
    }.get(ext, "image/jpeg")


# ─── Vendor 1: GPT ───────────────────────────────────────────────────────


def analyze_with_openai(image_path: Path) -> TyreCondition:
    """Analyze a tyre image using GPT vision."""
    b64 = load_image_as_base64(image_path)
    response = openai_client.chat.completions.parse(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Please analyze this tyre image and provide a structured assessment.",
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{media_type_for(image_path)};base64,{b64}"},
                    },
                ],
            },
        ],
        response_format=TyreCondition,
    )
    return cast(TyreCondition, response.choices[0].message.parsed)


# ─── Vendor 2: Claude Opus ───────────────────────────────────────────────


def analyze_with_anthropic(image_path: Path) -> TyreCondition:
    """Analyze a tyre image using Claude Opus."""
    b64 = load_image_as_base64(image_path)
    response = anthropic_client.messages.create(  # type: ignore[call-overload]
        model=ANTHROPIC_MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Please analyze this tyre image and provide a structured assessment.",
                    },
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type_for(image_path),
                            "data": b64,
                        },
                    },
                ],
            }
        ],
        tools=[
            {"name": "report_tyre_condition", "input_schema": TyreCondition.model_json_schema()}
        ],
        tool_choice={"type": "tool", "name": "report_tyre_condition"},
    )
    tool_use_block = next(b for b in response.content if b.type == "tool_use")
    return TyreCondition.model_validate(tool_use_block.input)


# ─── Cross-evaluation (each model audits the other's output) ─────────────


def gpt_evaluates_claude(image_path: Path, claude_result: TyreCondition) -> CrossEvaluation:
    """Audit Claude's tyre assessment using GPT. Returns a CrossEvaluation."""
    response = openai_client.chat.completions.parse(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": CROSS_EVAL_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Other model's assessment:\n"
                        + claude_result.model_dump_json(indent=2),
                    },
                    {"type": "text", "text": "Now evaluate that assessment against the image:"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type_for(image_path)};base64,{load_image_as_base64(image_path)}"
                        },
                    },
                ],
            },
        ],
        response_format=CrossEvaluation,
    )
    return cast(CrossEvaluation, response.choices[0].message.parsed)


def claude_evaluates_gpt(image_path: Path, gpt_result: TyreCondition) -> CrossEvaluation:
    """Audit GPT's tyre assessment using Claude. Returns a CrossEvaluation."""
    response = anthropic_client.messages.create(  # type: ignore[call-overload]
        model=ANTHROPIC_MODEL,
        max_tokens=1024,
        system=CROSS_EVAL_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Other model's assessment:\n"
                        + gpt_result.model_dump_json(indent=2),
                    },
                    {"type": "text", "text": "Now evaluate that assessment against the image:"},
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type_for(image_path),
                            "data": load_image_as_base64(image_path),
                        },
                    },
                ],
            }
        ],
        tools=[
            {"name": "evaluate_other_model", "input_schema": CrossEvaluation.model_json_schema()}
        ],
        tool_choice={"type": "tool", "name": "evaluate_other_model"},
    )
    tool_use_block = next(b for b in response.content if b.type == "tool_use")
    return CrossEvaluation.model_validate(tool_use_block.input)


# ─── Parallel orchestration ──────────────────────────────────────────────


def analyze_in_parallel(image_path: Path) -> tuple[TyreCondition, TyreCondition]:
    """Run both vision models on the same image concurrently."""
    with ThreadPoolExecutor(max_workers=2) as ex:
        gpt_future = ex.submit(analyze_with_openai, image_path)
        claude_future = ex.submit(analyze_with_anthropic, image_path)
        return gpt_future.result(), claude_future.result()


def cross_evaluate_in_parallel(
    image_path: Path,
    gpt_result: TyreCondition,
    claude_result: TyreCondition,
) -> tuple[CrossEvaluation, CrossEvaluation]:
    """Run both cross-evaluations concurrently."""
    with ThreadPoolExecutor(max_workers=2) as ex:
        gpt_eval_future = ex.submit(gpt_evaluates_claude, image_path, claude_result)
        claude_eval_future = ex.submit(claude_evaluates_gpt, image_path, gpt_result)
        return gpt_eval_future.result(), claude_eval_future.result()


# ─── Reporting ───────────────────────────────────────────────────────────


def print_comparison(
    image_name: str,
    gpt: TyreCondition,
    claude: TyreCondition,
    gpt_eval_of_claude: CrossEvaluation | None = None,
    claude_eval_of_gpt: CrossEvaluation | None = None,
) -> None:
    """
    Print a side-by-side comparison of the two model outputs, plus cross-evals.

    TODO: design and implement the formatting.

    Suggestions:
    - Header with image name
    - Score table comparing safety_score, tread_depth, confidence per model
    - Each model's overall_condition and recommended_action
    - Each model's visible_issues as bullets
    - Each model's summary_for_ops_director
    - Cross-eval section: who rated whom how, what each said the other missed
    - "DELTA" section highlighting where they DISAGREE — the interesting bit
    """
    print(f"\n=== {image_name} ===")
    print(f"GPT: {gpt}")
    print(f"Claude: {claude}")
    if gpt_eval_of_claude:
        print(f"\nGPT's evaluation of Claude:\n{gpt_eval_of_claude}")
    if claude_eval_of_gpt:
        print(f"\nClaude's evaluation of GPT:\n{claude_eval_of_gpt}")


# ─── Main ────────────────────────────────────────────────────────────────


def main() -> None:
    here = Path(__file__).parent
    images = [here / "punctured_tyre.png", here / "bad_tyre.png"]

    for img in images:
        if not img.exists():
            print(f"⚠ Image not found: {img}")
            continue

        print(f"\n{'━' * 70}")
        print(f"  ANALYZING: {img.name}")
        print(f"{'━' * 70}")

        print("→ Running both models in parallel...", flush=True)
        gpt_result, claude_result = analyze_in_parallel(img)

        print("→ Cross-evaluating in parallel...", flush=True)
        gpt_eval_of_claude, claude_eval_of_gpt = cross_evaluate_in_parallel(
            img, gpt_result, claude_result
        )

        print_comparison(
            img.name, gpt_result, claude_result, gpt_eval_of_claude, claude_eval_of_gpt
        )


if __name__ == "__main__":
    main()
