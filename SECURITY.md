# Security policy

## Reporting a vulnerability

If you believe you've found a security vulnerability in siphyy-core, please report it **privately** by emailing **surajit.das0320@gmail.com**.

**Please do not open a public GitHub issue for security-sensitive reports.** Public issues are visible to everyone the moment they're filed and could expose users before a fix is available.

We aim to:

- Acknowledge your report within **72 hours**.
- Have a patch or mitigation in place within **14 days** for confirmed vulnerabilities — typically faster.
- Coordinate disclosure timing with you so users have a chance to update before details go public.

If you'd prefer encrypted communication, mention so in your initial email and we'll arrange a key exchange.

## Supported versions

| Version | Status |
|---|---|
| `0.1.x` (alpha) | Supported — currently the only released line |
| < `0.1.0` | Unsupported (no public releases) |

While the project is in alpha, security fixes ship in the next minor release. Once `1.0` lands we'll publish a longer-term support matrix.

## Scope

**In scope** for this policy:

- Code under `src/siphyy/`
- The Streamlit demo app under `apps/demo/`
- The CI and deploy workflows under `.github/workflows/`
- Anything else this repository directly publishes

**Out of scope** (please report elsewhere):

- Vulnerabilities in third-party LLM providers (OpenAI, Anthropic, Gemini, …) — report directly to the provider.
- Vulnerabilities in the underlying Python interpreter or in third-party libraries we depend on — report upstream (or open a regular issue here if there's a siphyy-specific mitigation we should ship).
- The proprietary **Siphyy Knowledge Pack** — that codebase is not in this repository and has its own reporting channel.

## What we consider a vulnerability

- **Yes**: code-execution paths via crafted input (telematics rows, LLM responses, uploaded files in the demo), credential leakage, deserialization gadgets, supply-chain compromise of our published artefacts.
- **Probably yes**: denial-of-service against the demo app, prompt-injection vectors that cause the agent to leak sensitive context, misconfiguration defaults that risk customer-data exposure.
- **Probably not**: missing best-practice hardening that doesn't have a concrete exploit path. Open a regular issue for those.

## Acknowledgements

Once a fix is released we're happy to credit you publicly (in the changelog and the release notes), or keep your report confidential — your preference. Tell us which when you report.
