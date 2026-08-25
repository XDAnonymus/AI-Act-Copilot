import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.ingestion import build_index


if __name__ == "__main__":
    manifest = build_index()
    print(f"Index ready: {manifest['chunk_count']} chunks")
