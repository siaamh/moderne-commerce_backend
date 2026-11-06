# ---------------------------------------------------------------------------
# Stage: runtime
# ---------------------------------------------------------------------------
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings

WORKDIR /app

# Install system dependencies required by psycopg2 and Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project source
COPY . .

# Collect static files.
# A dummy SECRET_KEY is used only during the build step; it is not baked
# into any runtime configuration and is overridden by the real .env at startup.
RUN SECRET_KEY=build-only-dummy-key DB_HOST=dummy DB_PASSWORD=dummy \
    python manage.py collectstatic --noinput

# Create a non-root user and transfer ownership
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
RUN chown -R appuser:appgroup /app
USER appuser

EXPOSE 8000

CMD ["sh", "start.sh"]
