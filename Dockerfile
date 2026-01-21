# Public API (RapidAPI contract) - production container
# Works great on Render for long-run stability.

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install deps first for better layer caching
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . /app

# Render (and most platforms) set PORT automatically
# We bind to 0.0.0.0 so it's reachable externally.
CMD ["sh", "-c", "uvicorn api_public_main:app --host 0.0.0.0 --port ${PORT:-8000}"]
