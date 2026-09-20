# Lightweight runtime image; dependencies are installed at build time so
# `docker compose up --build` performs the install automatically.
FROM python:3.12-slim

# Do not buffer stdout/stderr; do not write .pyc files into the image.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /srv

# Install dependencies first for better layer caching.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source.
COPY app ./app

# Run as the unprivileged user shipped with the image.
USER nobody

EXPOSE 8000

# Container-internal health check using the stdlib only (no curl in slim).
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import json,urllib.request,sys; sys.exit(0 if json.load(urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3))['status']=='ok' else 1)"

# `exec` so uvicorn receives SIGTERM directly for a clean shutdown.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level ${LOG_LEVEL:-info}"]
