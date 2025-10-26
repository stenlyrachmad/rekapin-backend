# worker.Dockerfile

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir --default-timeout=120 -r requirements.txt -i https://pypi.org/simple


# Copy all app code
COPY . .

# Default command: run RQ worker
CMD ["rq", "worker", "-u", "redis://redis:6379/0", "summaries"]
