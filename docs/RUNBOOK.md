# Windows / PowerShell Runbook

## Assumptions

- Windows 10/11.
- Python 3.12 is installed.
- Docker Desktop is installed for the container run.
- Ollama is already running on the host.
- `qwen3.8:latest` and `embeddinggemma:latest` are already available in Ollama.

## Local PowerShell Run

```powershell
git clone https://github.com/XDAnonymus/AI-Act-Copilot.git
cd eu-ai-act-copilot

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

Copy-Item .env.example .env
python scripts/download_sources.py
python scripts/ingest.py
python -m pytest -q
python scripts/smoke_test.py
streamlit run app/ui.py
```

Open `http://localhost:8501`.

## Generate Submission Metrics

```powershell
python scripts/evaluate.py
python scripts/load_test.py --requests 50 --concurrency 1
```

Or run all checks:

```powershell
.\scripts\run_submission.ps1
```

Review:

```text
results/evaluation.md
results/load_test.md
```

## Docker Run

Build:

```powershell
docker build -t eu-ai-act-copilot .
```

Run:

```powershell
docker run --rm -p 8501:8501 eu-ai-act-copilot
```

The image connects to the Windows-host Ollama instance using:

```text
http://host.docker.internal:11434
```

On first container start the entrypoint builds the local Qdrant index, then launches Streamlit.

## Download the original data sources (PDFs)

To download the exact pinned files:

```powershell
python scripts/download_sources.py
```

If an official file has changed, the SHA256 check intentionally fails.

## Common Problems

### `Vector index is missing`

```powershell
python scripts/ingest.py
```

### Docker cannot reach Ollama

Confirm Ollama is running on Windows. The Docker image already uses `host.docker.internal`, not `localhost`.

### Port 8501 is busy

```powershell
docker run --rm -p 8502:8501 eu-ai-act-copilot
```

Then open `http://localhost:8502`.
