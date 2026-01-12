# Python scraper container for Cloudflare Containers
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml .
COPY src/ ./src/
COPY scraper/ ./scraper/
COPY container/server.py .

# Install Python dependencies
RUN pip install --no-cache-dir -e . gunicorn flask

# Expose port
EXPOSE 8080

# Run the server
CMD ["gunicorn", "-b", "0.0.0.0:8080", "-w", "1", "--timeout", "300", "server:app"]
