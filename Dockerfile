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

# Make entrypoint executable
RUN chmod +x entrypoint.sh

# Run entrypoint
ENTRYPOINT ["/bin/bash", "entrypoint.sh"]
