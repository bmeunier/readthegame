# Dockerfile
FROM python:3.11-slim

# System deps (psycopg needs them)
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Increase pip network timeout (your log showed a timeout)
ENV PIP_DEFAULT_TIMEOUT=180

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Make sure your code actually gets into the image
COPY . /app

# Ensure Python can import "src.*"
ENV PYTHONPATH=/app

EXPOSE 8000
# The actual server command comes from docker-compose.yml