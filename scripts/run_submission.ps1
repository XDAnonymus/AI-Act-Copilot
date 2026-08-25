$ErrorActionPreference = "Stop"

python -m pip install -r requirements.txt
python scripts/download_sources.py
python scripts/ingest.py
python -m pytest -q
python scripts/smoke_test.py
python scripts/evaluate.py
python scripts/load_test.py --requests 50 --concurrency 1

Write-Host "Submission checks completed. Review results/evaluation.md and results/load_test.md."
