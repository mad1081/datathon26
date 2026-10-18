ARG VLLM_BASE_IMAGE=vllm/vllm-openai:v0.31.0@sha256:c1c9f6fd5c109ba7f0546a59f5b2f15fb87f64c77782e90a27b648b42a8e67c3
FROM ${VLLM_BASE_IMAGE}

# Stable vLLM requires Transformers <5.18; MiniCPM 4.7 needs the pinned
# nightly base and Transformers 5.18.0. prepare mode selects both together.
ARG TRANSFORMERS_VERSION=5.17.0
RUN python3 -m pip install --no-cache-dir "transformers==${TRANSFORMERS_VERSION}"

WORKDIR /opt/forte
COPY models.json serve.py smoke_multi_image.py download_weights.py ./
ENTRYPOINT ["python3", "/opt/forte/serve.py"]

