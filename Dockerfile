FROM python:3.12-slim

# Install curl + Node.js (for Circle API bridge)
RUN apt-get update && apt-get install -y curl gnupg2 && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy and install Node deps (Circle SDK)
COPY scripts/package.json scripts/
COPY scripts/package-lock.json scripts/
RUN cd scripts && npm install

# Copy app
COPY . .

# Run directly (no startup script to reduce memory)
CMD ["uvicorn", "serve:app", "--host", "0.0.0.0", "--port", "8080"]
