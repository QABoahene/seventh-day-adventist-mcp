"""Build the full database by running every ingestion script in order.

Usage: python scripts/build_all.py
"""

import subprocess
import sys
from pathlib import Path

SCRIPTS = ["ingest_bible.py", "ingest_beliefs.py", "ingest_egw.py"]


def main() -> None:
    here = Path(__file__).resolve().parent
    for name in SCRIPTS:
        print(f"\n=== {name}")
        result = subprocess.run([sys.executable, str(here / name)])
        if result.returncode != 0:
            sys.exit(f"{name} failed with exit code {result.returncode}")
    print("\nDatabase ready.")


if __name__ == "__main__":
    main()
