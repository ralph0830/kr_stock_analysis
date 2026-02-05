# Database Initialization - One-time execution
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy lib package for installation
COPY lib/ /app/lib/
COPY scripts/ /app/scripts/
COPY src/ /app/src/

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN cd /app/lib && pip install --no-cache-dir .

# Set Python path
ENV PYTHONPATH=/app:$PYTHONPATH

# Default command
CMD ["python", "/app/scripts/init_db.py"]
