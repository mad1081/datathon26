# CPU/mock (default):   docker build -t cashcheck .
# GPU transformers:     docker build -t cashcheck:gpu \
#                         --build-arg BASE=pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime \
#                         --build-arg WITH_TRANSFORMERS=1 .
ARG BASE=python:3.11-slim
FROM ${BASE}
ARG WITH_TRANSFORMERS=0
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt requirements-gpu.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && if [ "$WITH_TRANSFORMERS" = "1" ]; then pip install --no-cache-dir -r requirements-gpu.txt; fi
COPY app ./app
COPY eval ./eval
COPY tests/make_synthetic.py ./tests/make_synthetic.py
COPY rules.json ./rules.json
ENV DATA_DIR=/data RULES_PATH=/app/rules.json VLM_BACKEND=mock HF_HOME=/models
VOLUME ["/data", "/models"]
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
