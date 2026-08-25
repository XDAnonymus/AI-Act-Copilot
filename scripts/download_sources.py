import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import hashlib

import httpx
import yaml

from app.config import BASE_DIR, settings


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


with open(settings.sources_file, "r", encoding="utf-8") as file:
    sources = yaml.safe_load(file)["sources"]

for source in sources:
    destination = BASE_DIR / source["path"]
    destination.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {source['title']}")
    response = httpx.get(source["url"], follow_redirects=True, timeout=120)
    response.raise_for_status()
    data = response.content
    actual_hash = sha256_bytes(data)
    expected_hash = source.get("sha256")
    if expected_hash and actual_hash.lower() != expected_hash.lower():
        raise RuntimeError(
            f"Downloaded file changed for {source['source_id']}: {actual_hash} != {expected_hash}. "
            "Review the new official version before updating sources.yaml."
        )
    destination.write_bytes(data)
    print(f"Saved {destination} ({len(data)} bytes)")
