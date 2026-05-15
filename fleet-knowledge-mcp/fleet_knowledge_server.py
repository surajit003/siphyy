"""
Fleet Knowledge MCP Server — RAG over fleet operations documents.

Indexes the knowledge_base/ directory at startup using OpenAI embeddings,
caches the result to index_cache.json (invalidates if any doc changes),
then serves semantic search via the search_knowledge tool.
"""

import hashlib
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from openai import OpenAI

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)-7s [fleet-knowledge] %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("fleet-knowledge")

# Load .env from this directory, then fall back to parent (siphyy-core/.env)
# so the OpenAI key flows through whether you set it locally or at the repo root.
load_dotenv(Path(__file__).parent / ".env")
load_dotenv(Path(__file__).parent.parent / ".env")

if not os.environ.get("OPENAI_API_KEY"):
    log.error("OPENAI_API_KEY not set; cannot embed documents.")
    sys.exit(1)

client = OpenAI()
KB_DIR = Path(__file__).parent / "knowledge_base"
CACHE_PATH = Path(__file__).parent / "index_cache.json"
EMBED_MODEL = "text-embedding-3-small"


def _load_docs() -> list[dict]:
    docs = []
    for md_path in sorted(KB_DIR.glob("*.md")):
        docs.append({"source": md_path.name, "text": md_path.read_text()})
    log.info("loaded %d docs from %s", len(docs), KB_DIR.name)
    return docs


def _embed(text: str) -> list[float]:
    resp = client.embeddings.create(model=EMBED_MODEL, input=text)
    return resp.data[0].embedding


def _build_or_load_index() -> list[dict]:
    docs = _load_docs()
    fingerprint = hashlib.md5(
        json.dumps([d["text"] for d in docs], sort_keys=True).encode()
    ).hexdigest()

    if CACHE_PATH.exists():
        cached = json.loads(CACHE_PATH.read_text())
        if cached.get("fingerprint") == fingerprint:
            log.info("loaded %d embeddings from cache", len(cached["docs"]))
            return cached["docs"]
        log.info("cache stale (docs changed); rebuilding")

    log.info("embedding %d docs via %s...", len(docs), EMBED_MODEL)
    for doc in docs:
        doc["embedding"] = _embed(doc["text"])
    CACHE_PATH.write_text(json.dumps({"fingerprint": fingerprint, "docs": docs}))
    log.info("cached %d embeddings to %s", len(docs), CACHE_PATH.name)
    return docs


INDEX = _build_or_load_index()
mcp = FastMCP("fleet-knowledge")
log.info("starting fleet-knowledge MCP server (%d docs indexed)", len(INDEX))


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


@mcp.tool()
def search_knowledge(query: str, top_k: int = 3) -> list[dict]:
    """
    Search internal fleet operations documents — maintenance manuals,
    diagnostic procedures, incident postmortems, safety policies — for
    content semantically relevant to the query.

    Use this when the user asks 'how do I...', 'what does it mean
    when...', 'what's the procedure for...', or any question that needs
    information from unstructured documents rather than structured fleet
    data (vehicle status, scheduled services).

    Args:
        query: Natural language question or topic.
        top_k: Number of most-relevant excerpts to return (default 3).

    Returns:
        List of {source, excerpt, similarity_score} dicts sorted by
        relevance (best first). similarity_score is cosine similarity
        between query and document embeddings (1.0 = identical meaning,
        0.0 = unrelated).
    """
    log.info("tool=search_knowledge query=%r top_k=%d", query, top_k)
    qvec = _embed(query)
    scored = [(_cosine(qvec, d["embedding"]), d) for d in INDEX]
    scored.sort(key=lambda x: x[0], reverse=True)
    results = [
        {
            "source": d["source"],
            "excerpt": d["text"],
            "similarity_score": round(s, 3),
        }
        for s, d in scored[:top_k]
    ]
    log.debug(
        "top scores: %s",
        [f"{r['source']}={r['similarity_score']}" for r in results],
    )
    return results


if __name__ == "__main__":
    mcp.run()
