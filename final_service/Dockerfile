# App only (expects a local vLLM reachable via VLM_BASE_URL). For one-pod deployment see deploy/README_DEPLOY.md.
ARG BASE=python:3.11-slim
FROM ${BASE}
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY rules.json ./rules.json
ENV DATA_DIR=/data RULES_PATH=/app/rules.json VLM_BASE_URL=http://vllm:8000/v1
VOLUME ["/data"]
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
