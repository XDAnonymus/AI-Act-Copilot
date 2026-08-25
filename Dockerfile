FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OLLAMA_BASE_URL=http://host.docker.internal:11434

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN python scripts/download_sources.py
RUN chmod +x docker-entrypoint.sh

EXPOSE 8501

ENTRYPOINT ["./docker-entrypoint.sh"]
