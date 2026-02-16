# Python scraper container for Cloudflare Containers
FROM python:3.11-slim

# Install system dependencies for git and Playwright browsers
RUN apt-get update && apt-get install -y \
    git \
    curl \
    # Playwright dependencies
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libatspi2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
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

# Run crawl4ai setup to install Playwright browsers and dependencies
RUN crawl4ai-setup

# Expose port
EXPOSE 8080

# Run the server
CMD ["gunicorn", "-b", "0.0.0.0:8080", "-w", "1", "--timeout", "300", "server:app"]
