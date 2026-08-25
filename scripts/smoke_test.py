import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.retrieval import Retriever


def main() -> None:
    with Retriever() as retriever:
        if not retriever.ready():
            raise SystemExit("Index missing. Run: python scripts/ingest.py")

        hits = retriever.search(
            "What is an AI system under the EU AI Act?",
            limit=3,
        )

        if not hits:
            raise SystemExit("Retrieval returned no evidence")

        print("Smoke test passed")
        for hit in hits:
            print(
                f"- {hit['title']} "
                f"p.{hit.get('page')} "
                f"score={hit.get('score', 0):.3f}"
            )


if __name__ == "__main__":
    main()
