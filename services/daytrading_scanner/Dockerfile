# ============================================================================
# Daytrading Scanner Service - Multi-stage Dockerfile
# ============================================================================

# Stage 1: Builder
FROM python:3.11-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Build lib package first
WORKDIR /build
COPY lib/ lib/
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -e ./lib

# Install service dependencies
WORKDIR /build/service
COPY services/daytrading_scanner/pyproject.toml ./
RUN pip install --no-cache-dir -e .

# Stage 2: Development (hot reload)
FROM python:3.11-slim AS development

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH="/app:$PYTHONPATH"

WORKDIR /app
# Copy service code with consistent path structure
COPY services/daytrading_scanner/ ./services/daytrading_scanner/

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5115/health || exit 1

# Expose port
EXPOSE 5115

# Run with hot reload (use consistent module path)
CMD ["uvicorn", "services.daytrading_scanner.main:app", "--host", "0.0.0.0", "--port", "5115", "--reload"]

# Stage 3: Production Runtime
FROM python:3.11-slim AS production

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH="/app:$PYTHONPATH"

# Set up application directory
WORKDIR /app
RUN mkdir -p /app/logs && \
    chown -R appuser:appuser /app

# Copy application code (services + src for fallback import)
COPY services/daytrading_scanner/ ./services/daytrading_scanner/
COPY src/ ./src/

# Change to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5115/health || exit 1

# Expose port
EXPOSE 5115

# Run application
CMD ["uvicorn", "services.daytrading_scanner.main:app", "--host", "0.0.0.0", "--port", "5115"]
