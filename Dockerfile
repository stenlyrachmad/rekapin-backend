# Base lightweight image
FROM python:3.11-slim

# Prevent Python from writing pyc files and buffering output
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc curl && \
    rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip

# Copy project files
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --default-timeout=120 -r requirements.txt -i https://pypi.org/simple

# Copy the rest of the app
COPY . .

# Expose port for FastAPI
EXPOSE 8000

# Start FastAPI server (Uvicorn)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
