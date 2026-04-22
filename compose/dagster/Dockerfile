# Stage 4 §4.3 prerequisite — buildable Dagster Lite image.
#
# The previous compose configuration referenced ``dagster/dagster:1.7.16``,
# which is not a published Docker Hub image (verified via Hub API: "object
# not found"). This blocked any attempt to bring up the Lite stack via
# ``docker compose up`` and prevented collecting real e2e PASS evidence
# for §4.3 promotion.
#
# This image is the minimal "Dagster Lite" runtime that assembly's
# ``DagsterWebserverProbe`` (HTTP probe to ``/server_info``) and
# ``ComposeRunningProbe`` for ``dagster-daemon`` (docker compose ps
# liveness) need to satisfy. It does NOT carry any business code — full
# Phase 0-3 execution belongs to a future stage with PG/Iceberg
# materialize wiring (see orchestrator/CLAUDE.md). This image is
# sufficient to:
#   * respond to ``dagster-daemon liveness-check``
#   * serve ``dagster-webserver`` on port 3000 (including ``/server_info``)
#   * use Postgres-backed run/event/schedule storage (matches the
#     DAGSTER_POSTGRES_* env block in compose/bundles/dagster.yaml)
#
# Pin matches orchestrator/pyproject.toml: ``dagster>=1.7,<1.10`` requires
# Python 3.12 (no 3.13/3.14 wheels available; codex stage 2.5 review #3
# documented this constraint).

FROM python:3.12-slim

# psycopg2 (used by dagster-postgres) needs libpq-dev at build time + libpq5
# at runtime. build-essential covers the C compiler psycopg2 wheel-source
# fallback path needs on platforms where the binary wheel doesn't exist.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libpq5 \
        curl \
 && rm -rf /var/lib/apt/lists/*

# Pin matches orchestrator/pyproject.toml ``dagster>=1.7,<1.10``. The
# psycopg2-binary fallback avoids the wheel-build cost when the platform
# wheel is available.
RUN pip install --no-cache-dir \
        "dagster>=1.7,<1.10" \
        "dagster-webserver>=1.7,<1.10" \
        "dagster-postgres>=0.23,<0.27" \
        "psycopg2-binary>=2.9,<3.0"

# DAGSTER_HOME holds dagster.yaml (instance config — Postgres storage)
# and workspace.yaml (locations to load — empty for Lite probe-only mode).
ENV DAGSTER_HOME=/opt/dagster/dagster_home
RUN mkdir -p "${DAGSTER_HOME}"

COPY dagster.yaml "${DAGSTER_HOME}/dagster.yaml"
COPY workspace.yaml "${DAGSTER_HOME}/workspace.yaml"

WORKDIR /opt/dagster/dagster_home
