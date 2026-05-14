# Tier 1 vs Tier 2

The detection pipeline is split into two layers with very different cost profiles, and matching responsibilities.

## Cost

| | Tier 1 | Tier 2 |
|---|---|---|
| Where | `siphyy.detectors` | `siphyy.agents` |
| Cost per event | microseconds, free | seconds, ~$0.001–0.01 per LLM call |
| Scales to | every telemetry row, all fleets | only "interesting" candidates |
| Determinism | fully deterministic | probabilistic, LLM-dependent |

For a 200-truck fleet polling every minute, that's ~300k events/day. Running an LLM on every one of them is the difference between $0.30/day and ~$3000/day on `gpt-4o-mini`. The tier split makes the framework economically viable, full stop.

## Responsibility

**Tier 1 is recall-oriented.**

- It should fire *generously*. Marginal cases warrant a Tier 2 look.
- A 15% threshold catches both real siphonage (40%+) and post-climb fuel settling (15-20%). The detector doesn't care which is which — that's Tier 2's job.
- False positives at Tier 1 are cheap (one extra LLM call). False negatives are expensive (missed siphonage costs the operator money).

**Tier 2 is precision-oriented.**

- It rules out the false positives Tier 1 surfaced.
- It uses the case base as grounding — `fuel_theft_0003` (thermal contraction), `fuel_theft_0006` (slope effect), and others teach the LLM what *isn't* theft.
- It produces a structured report with assessment, confidence, reasoning, and recommended actions — not a yes/no.

This split is non-negotiable. **If you find yourself adding "smarter" rules to Tier 1 to suppress false positives, stop.** That logic belongs at Tier 2, expressed as either a seed case or as extra context flowing into `InterestingEvent.evidence`.

## How they communicate

The wire between the tiers is `InterestingEvent`, defined in `siphyy.schema.interesting`:

```python
class InterestingEvent(BaseModel):
    detector_name: str
    vehicle_id: str
    timestamp: datetime
    category: InterestingCategory
    severity: Severity
    summary: str
    confidence: float
    evidence: dict[str, object]
    triggering_event_id: str | None
```

The interesting bit is `evidence` — a free-form dict where Tier 1 puts the numbers Tier 2 needs to reason. The detector says "fuel dropped 47%, prior reading was X, current is Y, the truck is parked at altitude Z" and the LLM reads all of that as part of its prompt.

Free-form `evidence` is a deliberate trade-off. A typed payload would catch typos earlier; a dict lets new detectors emit new keys without a schema migration. Tier 2's prompt-building handles whatever it gets — and the LLM is robust to occasional missing keys because the seed cases teach it which signals matter most.

## When to add a new tier

You probably shouldn't. The two tiers cover the precision/recall trade-off cleanly. If you're thinking of inserting a "Tier 1.5" — a slightly-smarter rule that runs before the LLM — that's a sign your seed cases need to do more work, not that the framework needs another layer.

Two real exceptions where extra structure is justified:

- **A pre-filter outside the framework.** If your data source already does coarse filtering (e.g., your telematics platform offers "only send me anomaly candidates"), use it; the framework's adapter sees fewer rows. That's a deployment optimisation, not a new tier.
- **Multi-agent orchestration.** If one report's verdict feeds another agent's input (e.g., a maintenance-risk agent that uses last week's fuel anomalies as context), you have an agent layer above Tier 2. Same Protocol shape; same precision-oriented contract.
