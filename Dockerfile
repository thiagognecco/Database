FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Run gunicorn with PORT env variable
CMD gunicorn -w 2 -b 0.0.0.0:${PORT:-8080} -k uvicorn.workers.UvicornWorker app.main:app
