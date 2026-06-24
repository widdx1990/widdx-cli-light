# WIDDX Cortex — Docker Image
# Usage:
#   docker build -t widdx-cortex .
#   docker run -it --rm -v $(pwd):/workspace -w /workspace widdx-cortex

FROM python:3.12-slim

LABEL org.opencontainers.image.title="WIDDX Cortex"
LABEL org.opencontainers.image.description="Terminal AI Workspace with UIL Cognitive Architecture"
LABEL org.opencontainers.image.authors="MUHAMMAD MUSLIH (WIDDX)"
LABEL org.opencontainers.image.url="https://github.com/widdx1990/widdx-cli-light"
LABEL org.opencontainers.image.licenses="MIT"

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY pyproject.toml /app/
COPY requirements.txt /app/ 2>/dev/null || true
WORKDIR /app
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e ".[dev]" 2>/dev/null || \
    pip install --no-cache-dir rich httpx textual prompt_toolkit pygments python-bidi

# Copy source
COPY . /app/

# Install the package
RUN pip install --no-cache-dir -e .

# ── Non-root user (security hardening) ────────────────────
RUN useradd --create-home --shell /bin/bash widdx \
    && chown -R widdx:widdx /app /workspace 2>/dev/null || true
USER widdx

# Set up entrypoint
ENV WIDDX_HOME=/workspace
WORKDIR /workspace
ENTRYPOINT ["widdx"]
CMD ["--help"]
