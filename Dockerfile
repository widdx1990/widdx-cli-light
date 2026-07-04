# WIDDX Nexus — Docker Image
FROM python:3.12-slim

LABEL org.opencontainers.image.title="WIDDX Nexus"
LABEL org.opencontainers.image.description="Terminal AI Workspace with UIL Cognitive Architecture"
LABEL org.opencontainers.image.authors="MUHAMMAD MUSLIH (WIDDX)"
LABEL org.opencontainers.image.url="https://github.com/widdx1990/widdx-cli-light"
LABEL org.opencontainers.image.licenses="MIT"

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip

COPY . .
RUN pip install --no-cache-dir -e .

RUN useradd --create-home --shell /bin/bash widdx \
    && chown -R widdx:widdx /workspace 2>/dev/null || true
USER widdx

ENV WIDDX_HOME=/workspace
WORKDIR /workspace
ENTRYPOINT ["widdx"]
CMD ["--help"]
