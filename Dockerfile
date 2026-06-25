# Reproducible build environment for the Guía Abierta pipeline.
# WeasyPrint needs Pango/Cairo/GDK-PixBuf at runtime; GeoPandas/Fiona/pyproj
# ship binary wheels, so no system GDAL is required.
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf-2.0-0 \
        libffi-dev \
        libcairo2 \
        libharfbuzz0b \
    && rm -rf /var/lib/apt/lists/*

# uv for fast, lockfile-free dependency install.
COPY --from=ghcr.io/astral-sh/uv:0.11.24 /uv /uvx /bin/

WORKDIR /app

# Copy the project, then install the exact pinned versions from uv.lock
# into /app/.venv. --frozen fails if the lock is stale instead of drifting.
COPY . .
RUN uv sync --frozen

# The pipeline writes to data/ (cache) and output/ (the booklet PDF).
# Mount them to keep results on the host:
#   docker run --rm -v "$PWD/data:/app/data" -v "$PWD/output:/app/output" guiat
ENTRYPOINT ["uv", "run", "--frozen", "python", "main.py"]
CMD []
