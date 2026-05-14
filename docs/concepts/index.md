# Concepts

These pages explain *why* the framework is shaped the way it is. The tutorial taught you to use it; this section helps you decide how to extend it without breaking the architectural commitments.

- **[Architecture](architecture.md)** — the four layers (schema, adapter, detector, agent) and how data flows between them.
- **[Canonical schema](canonical-schema.md)** — the single contract everything past the adapter layer reasons in. Why fuel lives as first-class fields and not in `provider_extras`.
- **[Tier 1 vs Tier 2](tier-1-vs-tier-2.md)** — why detection is split into a cheap rule layer and an expensive grounded-LLM layer.
- **[Case base](case-base.md)** — how historical incidents feed Tier 2's reasoning, and why a "false positive" case is just as valuable as a confirmed-theft case.
