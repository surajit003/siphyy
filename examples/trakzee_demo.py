"""End-to-end example: translate a Trakzee export into canonical events.

Run:
    python examples/trakzee_demo.py /path/to/trakzee_export.xlsx
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from siphyy.adapters import TrakzeeAdapter


def main(xlsx_path: Path) -> None:
    df = pd.read_excel(
        xlsx_path,
        sheet_name="positions",
        dtype=str,
        keep_default_na=False,
    )

    print(f"Loaded {len(df)} rows from {xlsx_path.name}")

    adapter = TrakzeeAdapter()

    # Process the first 5 rows just for demo output
    sample_rows = df.head(5).to_dict(orient="records")
    events = list(adapter.adapt(sample_rows))

    print(f"\nTranslated {len(sample_rows)} rows -> {len(events)} canonical events\n")

    for i, event in enumerate(events, 1):
        print(f"--- Event {i} ---")
        print(event.model_dump_json(indent=2))
        print()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python examples/trakzee_demo.py <path-to-trakzee-export.xlsx>")
        sys.exit(1)
    main(Path(sys.argv[1]))
