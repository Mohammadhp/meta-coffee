# Meta-Coffee Django app
FROM python:3.14-slim

WORKDIR /app

# Install system deps (none needed — psycopg[binary] bundles libpq)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Collect static files (WhiteNoise)
RUN python manage.py collectstatic --noinput

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -fs http://localhost:8000/ || exit 1

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-"]
