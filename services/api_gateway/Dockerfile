# API Gateway Multi-stage Dockerfile
# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy lib package for installation
COPY lib/ /build/lib/
COPY services/api_gateway/pyproject.toml /build/

# Install ralph-stock-lib (includes shared dependencies)
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN cd lib && pip install --no-cache-dir .

# Stage 2: Development
FROM python:3.11-slim AS development

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy service code
COPY services/api_gateway/ /app/services/api_gateway/
COPY src/ /app/src/

# Install service dependencies
WORKDIR /app/services/api_gateway
RUN pip install --no-cache-dir -e .[dev]

# Set Python path
ENV PYTHONPATH=/app:/app/services/api_gateway:$PYTHONPATH

# Default command
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5111", "--reload"]

# Stage 3: Production
FROM python:3.11-slim AS production

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy service code (no tests, no docs)
COPY services/api_gateway/ /app/services/api_gateway/
COPY src/ /app/src/

# Install production dependencies only
WORKDIR /app/services/api_gateway
RUN pip install --no-cache-dir -e .

# Set Python path (include /app for src module imports)
ENV PYTHONPATH=/app:/app/services/api_gateway:$PYTHONPATH

# Non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:5111/health').raise_for_status()"

# Expose port
EXPOSE 5111

# Production command
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5111"]
