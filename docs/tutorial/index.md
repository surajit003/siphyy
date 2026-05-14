# Tutorial

This is the progressive path from "I just cloned the repo" to "I'm running siphyy against my own fleet data with an LLM I picked".

Follow the pages in order — each builds on the previous. None of them takes more than 10-15 minutes.

1. **[Install](install.md)** — uv, Python 3.14, the package.
2. **[Your first pipeline](first-pipeline.md)** — run the bundled sample data end-to-end. See an `InterestingEvent` fire and a `FuelAnomalyReport` come out.
3. **[Writing an adapter](writing-an-adapter.md)** — bring your own telematics provider in ~50 lines.
4. **[Writing a detector](writing-a-detector.md)** — add a new Tier 1 rule.
5. **[Using an LLM client](using-an-llm-client.md)** — swap OpenAI for Anthropic, or plug in your own provider in 20 lines.

When you're done with the tutorial, move on to [Concepts](../concepts/index.md) for the *why* behind the architecture, or [How-to](../how-to/index.md) for problem-driven recipes.
