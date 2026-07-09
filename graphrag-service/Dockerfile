FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV GRAPHRAG_DATA_ROOT=/app/data/case
ENV GRAPHRAG_BOOTSTRAP=auto

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY graphrag/ graphrag/
COPY scripts/ scripts/
COPY assets/ assets/
COPY data/ data/

CMD ["python3", "scripts/docker_entrypoint.py"]
