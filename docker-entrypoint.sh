#!/bin/sh
set -e

if [ ! -f data/.indexed ]; then
    echo "Vector index not found; building it now..."
    python scripts/ingest.py
fi

exec streamlit run app/ui.py \
    --server.address=0.0.0.0 \
    --server.port=8501 \
    --server.headless=true
