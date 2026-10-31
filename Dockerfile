FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN python -m pip install --no-cache-dir --upgrade "pip>=26.2" "setuptools>=84.1.0" \
    && python -m pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium browser and OS dependencies
RUN playwright install --with-deps chromium && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .

# Copy backend source code
COPY backend /app/backend

# Set working directory to backend to run uvicorn
WORKDIR /app/backend
ENV PYTHONPATH=/app/backend

# Run uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
