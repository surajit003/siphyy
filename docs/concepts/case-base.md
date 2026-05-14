# Case base

Tier 2 agents don't reason about fuel theft in the abstract. They reason about *this event* in light of *these prior incidents*. The case base is where the prior incidents live.

## What a case looks like

An `IncidentCase` (in `siphyy.schema.case`) carries:

- `case_id` — stable identifier (`fuel_theft_0001`).
- `category` — one of `fuel_theft`, `maintenance`, `driver_behavior`, `vehicle_issue`, `route_anomaly`, `false_positive`.
- `severity` — `low | medium | high | critical`.
- `region`, `vehicle_type` — context the agent can match on.
- `summary` — the symptoms as the detection system observed them. *This is what's embedded for similarity retrieval.* Write it in the same prose register as a Tier 1 detector's interesting-event payload.
- `diagnosis` — what was actually happening, established by investigation.
- `resolution` — concrete action taken.
- `lessons` — generalisable patterns. *This is what makes a case valuable beyond its specifics.*

A case is essentially: "we saw symptoms X, the cause turned out to be Y, here's what we did about it, and here's what's transferable to other cases."

## Why false-positive cases matter as much as true-positive ones

The seed case `fuel_theft_0003` is a *false positive* — overnight thermal contraction on a parked tanker that looked exactly like siphonage but wasn't. It's in the case base because:

- It teaches the LLM that overnight fuel "drops" can be benign.
- It gives the LLM a citable precedent when ruling something out.
- It quantifies the magnitude scale ("~14% over 22 minutes for a 12°C cooling on diesel") so the LLM can compare current events.

Without `fuel_theft_0003`, every overnight drop would look like siphonage to a naive LLM. The case is the framework's way of encoding domain knowledge declaratively, without writing thermal-contraction code.

`fuel_theft_0006` does the same job for post-climb fuel settling. Future framework expansions follow this pattern: *the cheapest way to teach the agent about a class of false positives is to add a seed case*, not to write more code.

## Retrieval

The current `CaseBase` is in-memory and filter-based — you can pull all `category="fuel_theft"` or `region="Zambia"` cases. The agent grabs both `fuel_theft` and `false_positive` cases and slots the first N into its prompt.

Embedding-based similarity retrieval is on the roadmap (pgvector-backed). The interface stays the same — `case_base.filter(...)` would just internally rank by embedding similarity before slicing. Agent code doesn't change.

## The synthetic seed cases vs the real-customer Knowledge Pack

The cases under `siphyy.knowledge.seed_cases` are *synthetic*. They're modelled on patterns common in African and emerging-market fleet operations, but no real customer data is encoded in them. They exist to:

1. Give a new deployment something to retrieve from before real cases accumulate.
2. Demonstrate the prose register expected for new case-base entries.
3. Serve as fixtures for the agent's tests.

Real customer-derived cases live in the proprietary **Siphyy Knowledge Pack** — not in this repository. The OSS framework runs perfectly well on just the seed cases; the paid Knowledge Pack adds curated cases, OEM manual content, and calibrated thresholds.

## Adding a case

When you encounter a new pattern worth teaching the agent, add an `IncidentCase` to `siphyy.knowledge.seed_cases` (for OSS-bundled examples) or to your own case base (for production deployments). The bar:

- The `summary` is concrete enough that a similar event's `InterestingEvent.summary` would semantically match it on retrieval.
- The `lessons` are written generalisably — *"large drops with engine off are almost never sensor noise"*, not *"this specific truck on this specific date was confirmed theft"*.
- For false positives, the diagnosis explains the *physical* cause (thermal, slope, sensor drift) — that's what makes the lesson transferable.
