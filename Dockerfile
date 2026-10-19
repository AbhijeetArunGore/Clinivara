# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm AS base

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies: Tesseract OCR, Leptonica, and security patches
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-hin \
    tesseract-ocr-mar \
    libmupdf-dev \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create unprivileged application user
RUN groupadd -r clinivara --gid 1001 && \
    useradd -r -g clinivara --uid 1001 --shell /bin/bash clinivara

WORKDIR /app

# Copy project manifests and source code
COPY pyproject.toml README.md ./
COPY clinivara/ ./clinivara/
COPY evaluation/ ./evaluation/

# Install Python dependencies using pip directly from manifest
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Pre-download spaCy English model for fast offline startup
RUN python -m spacy download en_core_web_sm

# Create segregated storage directories with restricted ownership
RUN mkdir -p /app/data/storage/boundary_a_raw \
             /app/data/storage/boundary_b_scratch \
             /app/data/storage/boundary_c_approved \
             /app/data/storage/token_vault \
             /app/data/storage/metadata \
             /app/data/audit && \
    chown -R clinivara:clinivara /app/data && \
    chmod -R 700 /app/data/storage

# Switch to unprivileged non-root user
USER clinivara

EXPOSE 8000

# Container healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "clinivara.main:app", "--host", "0.0.0.0", "--port", "8000"]
