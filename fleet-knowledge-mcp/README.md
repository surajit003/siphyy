# Fleet Knowledge — RAG MCP Server

A third MCP server that adds **unstructured knowledge** to the fleet ecosystem. Indexes maintenance manuals, incident postmortems, and operational policies stored as markdown in `knowledge_base/`. Uses OpenAI embeddings (`text-embedding-3-small`) for semantic retrieval.

## What it exposes

| Name | Signature | Purpose |
|---|---|---|
| `search_knowledge` | `(query: str, top_k: int = 3) -> list[dict]` | Semantic search across all documents in `knowledge_base/`. Returns top-K most relevant excerpts with similarity scores. |

## Setup

Requires `OPENAI_API_KEY` set in your environment or in a `.env` file (this directory, or the parent `siphyy-core/.env`).

```bash
uv venv --python 3.14
uv pip install -r requirements.txt
.venv/bin/python fleet_knowledge_server.py    # builds index on first run, ~3s
```

First startup embeds all docs (~10-15 API calls, half a cent total). Subsequent startups load from `index_cache.json` instantly. The cache invalidates automatically if any `.md` file in `knowledge_base/` changes.

## Try cross-server queries (after registering all three servers)

1. **"How do I diagnose a stuck fuel injector?"** — pure RAG; only `search_knowledge` fires.
2. **"KCA 891H had a tyre incident. What does our procedure say about pothole damage?"** — hybrid: `get_recent_incidents` (fleet-tools) + `search_knowledge` (this server).
3. **"What's the safest way to respond if KCA 891H breaks down?"** — `get_vehicle_status` + `search_knowledge`.
4. **"Compare what actually happened to KCA 891H with our official postmortem procedure."** — agentic-feeling: fetches incident, retrieves postmortem document, reasons over both.
5. **"Summarise everything you know about KBJ 445T including any relevant procedures."** — wide cross-server: all four tools across three servers.

## How it works inside

Three phases:

1. **Indexing** (startup): each `.md` file in `knowledge_base/` is chunked (whole-file for now) and sent to OpenAI's embedding API. Resulting vectors (1536 floats each) are cached to disk.
2. **Retrieval** (per tool call): the user query is embedded with the same model. Cosine similarity is computed against every document vector. Top-K returned.
3. **Generation**: Claude reads the retrieved excerpts and synthesises the answer.

The `similarity_score` in each result tells you how confident the retrieval was. Scores > 0.5 are strong; scores < 0.3 mean the retrieval probably missed and the answer should be treated with care.
