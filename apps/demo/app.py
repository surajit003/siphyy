"""Streamlit demo for the Siphyy fleet telematics framework.

Visualises the canonical schema → adapter → detector → agent pipeline
step by step, surfacing every LLM call (with the actual prompts) so a
fleet operator can see exactly what's happening inside the black box.

Run locally:
    streamlit run apps/demo/app.py

Run on HuggingFace Spaces: the README.md alongside this file carries
the Space frontmatter; pushing to the linked git repo redeploys.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st

from siphyy.adapters import TrakzeeAdapter
from siphyy.agents import (
    AnthropicLLMClient,
    FuelAnomalyAgent,
    FuelAnomalyReport,
    LLMClient,
    MockLLMClient,
    OpenAILLMClient,
)
from siphyy.agents.fuel_anomaly import _SYSTEM_PROMPT, _LLMVerdict
from siphyy.detectors import FuelSiphonageDetector
from siphyy.knowledge import SEED_CASES
from siphyy.schema import CaseBase, InterestingEvent

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SAMPLE_DATA_PATH = REPO_ROOT / "examples" / "data" / "sample_trakzee.json"


# ──────────────────────────────────────────────────────────────────────
# Page entry
# ──────────────────────────────────────────────────────────────────────


def main() -> None:
    st.set_page_config(
        page_title="Siphyy — Fleet Telematics Demo",
        page_icon="⛽",
        layout="wide",
    )

    st.title("Siphyy — fleet telematics pipeline")
    st.caption(
        "Provider-agnostic canonical schema → cheap Tier 1 detectors → "
        "LLM-grounded Tier 2 agents. Watch the whole pipeline run live."
    )

    _render_privacy_notice()
    config = _render_sidebar()
    rows = _render_input_section()

    if rows is None:
        st.info(
            "👈 Upload a Trakzee export (.json or .xlsx) or click **Use sample data** to begin."
        )
        return

    st.markdown(f"**{len(rows)} rows loaded.**")

    if st.button("▶ Run pipeline", type="primary", use_container_width=True):
        _run_pipeline(rows, config)


# ──────────────────────────────────────────────────────────────────────
# Sidebar / configuration
# ──────────────────────────────────────────────────────────────────────


def _render_sidebar() -> dict[str, str]:
    with st.sidebar:
        st.header("Configuration")
        provider = st.radio(
            "LLM provider",
            ["OpenAI", "Anthropic", "Mock (no key needed)"],
            help=(
                "Mock uses pre-written realistic verdicts so you can "
                "see the full pipeline without an API key."
            ),
        )

        api_key = ""
        model = ""
        if provider == "OpenAI":
            api_key = st.text_input(
                "OPENAI_API_KEY",
                type="password",
                help="Your key stays in your browser session — never logged.",
            )
            model = st.text_input("Model", value="gpt-4o-mini-2024-07-18")
        elif provider == "Anthropic":
            api_key = st.text_input(
                "ANTHROPIC_API_KEY",
                type="password",
                help="Your key stays in your browser session — never logged.",
            )
            model = st.text_input("Model", value="claude-haiku-4-5-20251001")
        else:
            st.info(
                "Will use **MockLLMClient** with realistic canned verdicts. No API calls are made."
            )

        st.divider()
        st.markdown(
            "🔗 [Repo on GitHub](https://github.com/surajit003/siphyy) · "
            "📄 [Quickstart](https://github.com/surajit003/siphyy#quickstart)"
        )

    return {"provider": provider, "api_key": api_key, "model": model}


# ──────────────────────────────────────────────────────────────────────
# Input section — upload or sample
# ──────────────────────────────────────────────────────────────────────


def _render_input_section() -> list[dict[str, Any]] | None:
    if "rows" not in st.session_state:
        st.session_state.rows = None
    if "rows_source" not in st.session_state:
        st.session_state.rows_source = ""

    col1, col2 = st.columns([3, 1])
    with col1:
        uploaded = st.file_uploader(
            "Trakzee export",
            type=["json", "xlsx"],
            accept_multiple_files=False,
            label_visibility="visible",
        )
    with col2:
        st.write("")
        st.write("")
        if st.button("📦 Use sample data", use_container_width=True):
            st.session_state.rows = json.loads(SAMPLE_DATA_PATH.read_text())
            st.session_state.rows_source = "sample_trakzee.json"

    if uploaded is not None:
        # Enforce a small size cap — the demo isn't built to chew through
        # a week of fleet data.
        max_bytes = 2 * 1024 * 1024  # 2 MB
        if uploaded.size and uploaded.size > max_bytes:
            st.error(
                f"File is {uploaded.size / 1024:.0f} KB — please use "
                f"a small sample (<{max_bytes // 1024} KB). For larger "
                f"datasets, clone the repo and run the library directly."
            )
            return None
        try:
            st.session_state.rows = _parse_upload(uploaded)
            st.session_state.rows_source = uploaded.name
        except (json.JSONDecodeError, ValueError) as e:
            st.error(f"Couldn't parse {uploaded.name}: {e}")
            st.session_state.rows = None

    if st.session_state.rows is not None and st.session_state.rows_source:
        st.success(f"Loaded **{st.session_state.rows_source}**.")

    return st.session_state.rows


def _parse_upload(uploaded: Any) -> list[dict[str, Any]]:
    name = uploaded.name.lower()
    if name.endswith(".json"):
        data = json.loads(uploaded.read().decode("utf-8"))
        if not isinstance(data, list):
            raise ValueError("JSON must be a list of row objects.")
        return data
    if name.endswith(".xlsx"):
        import pandas as pd

        df = pd.read_excel(uploaded, sheet_name="positions", dtype=str, keep_default_na=False)
        return df.to_dict(orient="records")
    raise ValueError(f"Unsupported file type: {uploaded.name}")


# ──────────────────────────────────────────────────────────────────────
# Pipeline runner
# ──────────────────────────────────────────────────────────────────────


def _run_pipeline(rows: list[dict[str, Any]], config: dict[str, str]) -> None:
    llm_client, llm_label = _build_llm_client(config)
    if llm_client is None:
        return

    # ── Step 1: Adapter ───────────────────────────────────────────
    with st.status(
        f"**Step 1 / 4 — Adapter**  (translating {len(rows)} provider rows)",
        expanded=True,
    ) as status:
        adapter = TrakzeeAdapter()
        events = list(adapter.adapt(rows))
        status.update(
            label=(
                f"**Step 1 / 4 — Adapter**  ✓ {len(events)} canonical TelemetryReadings produced"
            ),
            state="complete",
        )
        if events:
            with st.expander("Inspect a sample canonical event"):
                st.json(json.loads(events[0].model_dump_json()))

    # ── Step 2: Tier 1 detector ───────────────────────────────────
    with st.status(
        "**Step 2 / 4 — Tier 1 detector**  (cheap, deterministic rules)",
        expanded=True,
    ) as status:
        detector = FuelSiphonageDetector()
        interesting: list[InterestingEvent] = [
            ie for ev in events if (ie := detector.process(ev)) is not None
        ]
        status.update(
            label=(
                f"**Step 2 / 4 — Tier 1 detector**  ✓ fired on "
                f"{len(interesting)} / {len(events)} events"
            ),
            state="complete",
        )
        for ie in interesting:
            st.markdown(f"- **{ie.vehicle_id}** · `{ie.severity}` · {ie.summary}")
            with st.expander(f"Evidence for {ie.vehicle_id}"):
                st.json(_evidence_for_display(ie))

    if not interesting:
        st.warning(
            "No Tier 1 detections in this dataset — nothing to send to "
            "the agent. Try the sample data to see the full pipeline."
        )
        return

    # ── Step 3: Tier 2 agent ──────────────────────────────────────
    st.markdown(f"**Step 3 / 4 — Tier 2 agent**  (calling **{llm_label}** for each Tier 1 fire)")
    case_base = CaseBase(SEED_CASES)
    agent = FuelAnomalyAgent(llm_client=llm_client, case_base=case_base)

    reports: list[FuelAnomalyReport] = []
    for ie in interesting:
        report = _render_agent_step(ie, agent, case_base, llm_label)
        if report is not None:
            reports.append(report)

    # ── Step 4: Final reports ─────────────────────────────────────
    if reports:
        st.markdown("## Step 4 / 4 — Reports")
        for report in reports:
            _render_report_card(report)


def _render_agent_step(
    ie: InterestingEvent,
    agent: FuelAnomalyAgent,
    case_base: CaseBase,
    llm_label: str,
) -> FuelAnomalyReport | None:
    with st.status(
        f"Processing **{ie.vehicle_id}**…",
        expanded=True,
    ) as status:
        retrieved = (
            case_base.filter(category="fuel_theft") + case_base.filter(category="false_positive")
        )[: agent._max_cases]
        cited = ", ".join(c.case_id for c in retrieved) or "(none)"
        st.markdown(f"**📚 Retrieved historical cases:**  {cited}")

        # Build the same prompt the agent will send — for transparency.
        user_prompt = agent._build_user_prompt(ie, retrieved)
        with st.expander("📝 System prompt (sent to the LLM)"):
            st.code(_SYSTEM_PROMPT, language="text")
        with st.expander("📝 User prompt (with retrieved cases embedded)"):
            st.code(user_prompt, language="text")

        st.markdown(f"**📞 Calling {llm_label}…**")
        try:
            report = agent.process(ie)
        except Exception as e:
            st.error(f"LLM call failed: {type(e).__name__}: {e}")
            status.update(state="error")
            return None

        if report is None:
            st.warning("Agent declined to act on this event.")
            status.update(state="error")
            return None

        st.markdown(
            f"**✓ Verdict:** `{report.assessment}` · confidence **{report.confidence:.0%}**"
        )
        status.update(
            label=(
                f"Processing **{ie.vehicle_id}** → `{report.assessment}` ({report.confidence:.0%})"
            ),
            state="complete",
        )
        return report


# ──────────────────────────────────────────────────────────────────────
# LLM client construction
# ──────────────────────────────────────────────────────────────────────


def _build_llm_client(config: dict[str, str]) -> tuple[LLMClient | None, str]:
    provider = config["provider"]

    if provider == "Mock (no key needed)":
        return MockLLMClient(_canned_verdicts()), "MockLLMClient"

    if not config["api_key"]:
        st.error(
            f"Enter your **{provider}** API key in the sidebar to "
            f"proceed, or switch to **Mock (no key needed)**."
        )
        return None, ""

    if provider == "OpenAI":
        client = OpenAILLMClient(
            model=config["model"] or "gpt-4o-mini-2024-07-18",
            api_key=config["api_key"],
        )
        return client, f"OpenAI · {config['model']}"

    if provider == "Anthropic":
        client = AnthropicLLMClient(
            model=config["model"] or "claude-haiku-4-5-20251001",
            api_key=config["api_key"],
        )
        return client, f"Anthropic · {config['model']}"

    return None, ""


def _canned_verdicts() -> list[_LLMVerdict]:
    """Realistic verdicts for the bundled sample data. Order: siphonage, then
    slope-effect — matching how the sample's events fire by vehicle order."""
    return [
        _LLMVerdict(
            assessment="likely_siphonage",
            confidence=0.92,
            summary="Active siphonage strongly suggested — pattern matches fuel_theft_0001.",
            reasoning=(
                "The drop magnitude (47%) and elapsed time (18 minutes) almost "
                "exactly match historical case fuel_theft_0001, confirmed siphonage "
                "via covert camera. Engine off + ignition off rules out normal "
                "consumption. Thermal contraction (fuel_theft_0003) is implausible "
                "at this magnitude — that case attributed only ~14% over 22 minutes "
                "to a 12°C cooling, an order of magnitude less than what we see here."
            ),
            recommended_actions=[
                "Investigate driver immediately",
                "Pull GPS history for the prior 6 hours and compare against route",
                "Inspect tank for unauthorized siphon valves",
                "Photograph current fuel level for evidentiary purposes",
            ],
            referenced_case_ids=["fuel_theft_0001", "fuel_theft_0003"],
        ),
        _LLMVerdict(
            assessment="likely_false_positive",
            confidence=0.78,
            summary="Pattern matches post-climb fuel settling — likely sensor artifact.",
            reasoning=(
                "The 18% drop within 7 minutes of the vehicle coming to rest at "
                "altitude 1335 m closely resembles fuel_theft_0006 — a tanker with "
                "a longitudinal BLE probe parked at the top of a grade. Fuel "
                "re-distributes once engine vibration stops, dropping the apparent "
                "reading. The vehicle's high resting altitude is consistent with "
                "having just finished a climb. Manual dip-check should confirm "
                "before any action against the driver."
            ),
            recommended_actions=[
                "Request manual fuel dip-check before escalating",
                "Confirm vehicle route — was the vehicle climbing prior to parking?",
                "Enable Teltonika AVL IDs 256/257 on the FMB920 so future events "
                "carry explicit pitch data",
            ],
            referenced_case_ids=["fuel_theft_0006"],
        ),
    ]


# ──────────────────────────────────────────────────────────────────────
# Rendering helpers
# ──────────────────────────────────────────────────────────────────────


_VERDICT_EMOJI = {
    "likely_siphonage": "🔴",
    "likely_false_positive": "🟢",
    "uncertain": "🟡",
}


def _render_report_card(report: FuelAnomalyReport) -> None:
    emoji = _VERDICT_EMOJI.get(report.assessment, "⚪")
    with st.container(border=True):
        st.markdown(f"### {emoji}  {report.vehicle_id} — `{report.assessment}`")

        cols = st.columns([1, 1, 2])
        cols[0].metric("Confidence", f"{report.confidence:.0%}")
        cols[1].metric("Detector", report.detector_name)
        if report.referenced_case_ids:
            cols[2].markdown("**Cited cases**  \n" + ", ".join(report.referenced_case_ids))

        st.markdown(f"**Summary**  \n{report.summary}")
        st.markdown(f"**Reasoning**  \n{report.reasoning}")

        if report.recommended_actions:
            st.markdown("**Recommended actions**")
            for action in report.recommended_actions:
                st.markdown(f"- {action}")


def _evidence_for_display(ie: InterestingEvent) -> dict[str, Any]:
    """Render evidence values as plain JSON-compatible types."""
    out: dict[str, Any] = {}
    for k, v in ie.evidence.items():
        out[k] = v if isinstance(v, str | int | float | bool | type(None)) else str(v)
    return out


# ──────────────────────────────────────────────────────────────────────
# Privacy notice
# ──────────────────────────────────────────────────────────────────────


def _render_privacy_notice() -> None:
    with st.expander("🔒 Privacy & data handling — read me first"):
        st.markdown(
            """
- **Your data stays in your browser session.** Uploaded files are
  processed in memory only; nothing is persisted to disk or logged.
- **API keys are not stored.** They live only in your Streamlit session
  for the lifetime of this tab.
- **The LLM provider sees your data.** When you pick OpenAI or
  Anthropic, the canonical events and historical cases are sent to that
  provider as part of the prompt — that's how Tier 2 works. Pick the
  **Mock** option to see the full flow without sending anything to a
  real LLM.
- **Upload size cap: 2 MB.** This demo is for small samples, not full
  fleet exports. Use the library directly for production volumes.
"""
        )


if __name__ == "__main__":
    main()
