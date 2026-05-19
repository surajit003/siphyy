"""
Exercise 01 — Chunking: Naive vs Paragraph
==========================================

Series: Production RAG Practice (10 exercises, fleet-themed, vanilla Python)
Source lesson: Arpit Bhayani, "RAG in Production" — Lesson #1 (Chunking Strategy)


Use case (the concrete problem)
-------------------------------
Driver Joseph Mwangi has just submitted a verbose voice-to-text incident
report about vehicle KAY 234X near Voi on the Mombasa road. The dispatcher
at the operations centre wants to find specific details quickly:

    - "What was leaking?"
    - "Where on the vehicle did it leak from?"
    - "Was the vehicle moving when it happened?"

To answer those questions later (with RAG over many such reports), we
need to split the report into chunks first. The question this exercise
asks is:

    Does HOW we chunk the report affect whether the dispatcher
    can find the answer at all?

Spoiler: yes, dramatically. This file shows you why.


The concept (what production RAG demands)
-----------------------------------------
From the article:

    "Fixed-size chunking cuts sentences in half, separates questions
     from their answers in FAQ documents, and splits code across
     function boundaries."

In plain English: naive fixed-size chunking ("split every 200 characters")
is fast and easy — and silently broken in production. It severs sentences,
separates a fact from its context, and produces chunks that look reasonable
in isolation but lose meaning when retrieved.

The fix is structure-aware chunking — split on boundaries the document
ALREADY HAS (paragraphs, sentences, sections, AST nodes, table rows).
The author's structure already encodes meaning. Respect it.

This file implements both and shows the difference when you search.


What you'll see when you run it
-------------------------------
    $ python 01_chunking_naive_vs_paragraph.py

Three sections of output:
    1. The naive size-based chunks (every 200 chars).
    2. The paragraph chunks.
    3. A search for "brake fluid" — and where the surrounding context
       ("rear left wheel area") ends up in each scheme.

The lesson lands when you compare section 3's two results.
"""

INCIDENT_REPORT = """\
Vehicle KAY 234X had an unusual incident this morning near Voi on the Mombasa road. The driver Joseph Mwangi was approaching a steep descent when he noticed an unusual vibration in the steering wheel.

The vibration grew worse as Joseph applied the brakes. He pulled over to the roadside and inspected the vehicle carefully, walking around it twice. He noticed brake fluid pooling on the tarmac under the chassis. The leak appears to come from the rear left wheel area, based on the trail of fluid.

Joseph radioed dispatch immediately at 09:42 EAT. He reported the vehicle is stationary, the cargo is intact, and no other vehicles were involved. He is currently waiting for a recovery team.

Recommendation from Joseph: do not move the vehicle. The fluid loss appears slow but consistent. The recovery team should bring a flatbed truck, not a tow rope.
"""


def chunk_by_size(text: str, size: int) -> list[str]:
    """Naive chunking: split text into fixed-size character windows.

    This is what most tutorials teach. It's fast, simple, and wrong.
    """
    return [text[i : i + size] for i in range(0, len(text), size)]


def chunk_by_paragraphs(text: str) -> list[str]:
    """Structure-aware chunking: split on the boundaries the author wrote.

    Paragraphs encode 'one idea per block.' Respecting them keeps
    related facts together in the same chunk.
    """
    return [p.strip() for p in text.split("\n\n") if p.strip()]


def find_chunks_containing(chunks: list[str], phrase: str) -> list[tuple[int, str]]:
    """Return (index, chunk) pairs where the phrase appears (case-insensitive)."""
    return [(i, c) for i, c in enumerate(chunks) if phrase.lower() in c.lower()]


def has_full_context(chunk: str) -> bool:
    """Check whether a chunk preserves the full 'brake fluid + rear left wheel' context.

    This is our proxy for 'would the dispatcher get a useful answer?'
    """
    lower = chunk.lower()
    return "brake fluid" in lower and "rear left wheel" in lower


def demo() -> None:
    bar = "=" * 72

    print(bar)
    print("THE INCIDENT REPORT (raw text)")
    print(bar)
    print(INCIDENT_REPORT)

    print(bar)
    print("1. NAIVE CHUNKS — chunk_by_size(report, 200)")
    print(bar)
    naive = chunk_by_size(INCIDENT_REPORT, 200)
    for i, c in enumerate(naive):
        print(f"\n[chunk {i}]  ({len(c)} chars)")
        print(repr(c))

    print("\n" + bar)
    print("2. PARAGRAPH CHUNKS — chunk_by_paragraphs(report)")
    print(bar)
    para = chunk_by_paragraphs(INCIDENT_REPORT)
    for i, c in enumerate(para):
        print(f"\n[chunk {i}]  ({len(c)} chars)")
        print(repr(c))

    print("\n" + bar)
    print("3. SEARCH: where does 'brake fluid' end up — and is the")
    print("   context ('rear left wheel area') still in the same chunk?")
    print(bar)

    print("\n-- Naive chunking --")
    for i, c in find_chunks_containing(naive, "brake fluid"):
        print(f"\nchunk {i}: {c!r}")
        print(f"   Context preserved? {has_full_context(c)}")

    print("\n-- Paragraph chunking --")
    for i, c in find_chunks_containing(para, "brake fluid"):
        print(f"\nchunk {i}: {c!r}")
        print(f"   Context preserved? {has_full_context(c)}")

    print("\n" + bar)
    print("THE LESSON")
    print(bar)
    print(
        "Naive chunking severs 'brake fluid' from 'rear left wheel area'\n"
        "because the 200-char window cuts mid-sentence. Paragraph chunking\n"
        "keeps them together because Joseph wrote them in the same paragraph.\n"
        "\n"
        "In production RAG, 'the answer was right there but cut by an arbitrary\n"
        "boundary' is one of the most common silent failure modes. The fix is\n"
        "literally to respect structure the document already has."
    )


if __name__ == "__main__":
    demo()


# =============================================================================
# Expected output (abbreviated — the key section)
# =============================================================================
#
# 3. SEARCH: where does 'brake fluid' end up ...
#
# -- Naive chunking --
#
# chunk 1: '...He noticed brake fluid pooling on the tarmac under'
#    Context preserved? False    <-- 'rear left wheel area' got cut into chunk 2
#
# -- Paragraph chunking --
#
# chunk 1: 'The vibration grew worse ... He noticed brake fluid pooling
#           on the tarmac under the chassis. The leak appears to come
#           from the rear left wheel area, based on the trail of fluid.'
#    Context preserved? True     <-- whole answer in one chunk
#
# The dispatcher querying 'where is the brake fluid leaking from?' gets
# a USEFUL answer from paragraph chunking and a FRAGMENT from naive chunking.
# Same data, same query, same retrieval logic — just a different chunker.


# =============================================================================
# Your turn (do these tomorrow or whenever — not required tonight)
# =============================================================================
#
# Extension 1 — Sentence chunker.
#   Write `chunk_by_sentences(text: str) -> list[str]` that splits on
#   sentence boundaries (a regex like r'(?<=[.!?])\s+' is good enough).
#   Run it on the report. When is sentence chunking BETTER than paragraph
#   chunking? When is it WORSE?
#
# Extension 2 — Add metadata.
#   Change `chunk_by_paragraphs` to return list[dict] where each dict has:
#       {"content": str, "doc_id": str, "chunk_index": int, "char_count": int}
#   This is the bridge to Exercise 02 (structure-aware chunking with metadata).
#
# Extension 3 — Make it lazy.
#   Convert both chunkers to generators (yield instead of return).
#   Why might this matter when the input is a 50MB maintenance manual
#   instead of a 4-paragraph incident report?
