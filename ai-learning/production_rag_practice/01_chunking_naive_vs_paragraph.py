"""Show how naive fixed-size chunking severs an answer from its context,
while paragraph chunking keeps them together."""

INCIDENT_REPORT = """\
Vehicle KAY 234X had an unusual incident this morning near Voi on the Mombasa road. The driver Joseph Mwangi was approaching a steep descent when he noticed an unusual vibration in the steering wheel.

The vibration grew worse as Joseph applied the brakes. He pulled over to the roadside and inspected the vehicle carefully, walking around it twice. He noticed brake fluid pooling on the tarmac under the chassis. The leak appears to come from the rear left wheel area, based on the trail of fluid.

Joseph radioed dispatch immediately at 09:42 EAT. He reported the vehicle is stationary, the cargo is intact, and no other vehicles were involved. He is currently waiting for a recovery team.

Recommendation from Joseph: do not move the vehicle. The fluid loss appears slow but consistent. The recovery team should bring a flatbed truck, not a tow rope.
"""


def chunk_by_size(text: str, size: int) -> list[str]:
    return [text[i : i + size] for i in range(0, len(text), size)]


def chunk_by_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in text.split("\n\n") if p.strip()]


def has_full_context(chunk: str) -> bool:
    lower = chunk.lower()
    return "brake fluid" in lower and "rear left wheel" in lower


if __name__ == "__main__":
    query = "brake fluid"

    print("Naive chunking (size=200):")
    for i, c in enumerate(chunk_by_size(INCIDENT_REPORT, 200)):
        if query in c.lower():
            print(f"  chunk {i}: context preserved? {has_full_context(c)}")

    print("Paragraph chunking:")
    for i, c in enumerate(chunk_by_paragraphs(INCIDENT_REPORT)):
        if query in c.lower():
            print(f"  chunk {i}: context preserved? {has_full_context(c)}")
