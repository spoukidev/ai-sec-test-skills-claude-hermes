# Reproducible runner. Keys are passed at runtime only:
#   docker build -t aisec .
#   docker run --rm aisec run --models claude,hermes --suite ci --mock
#   docker run --rm -e ANTHROPIC_API_KEY -v "$PWD/results:/app/results" aisec run --models claude
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 AISEC_HOME=/app
COPY pyproject.toml README.md LICENSE ./
COPY aisec ./aisec
RUN pip install --no-cache-dir .
COPY config ./config
COPY skills ./skills
COPY payloads ./payloads
COPY fixtures ./fixtures
RUN useradd -m aisec && mkdir -p results && chown aisec results
USER aisec
ENTRYPOINT ["aisec"]
CMD ["list"]
