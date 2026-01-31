FROM python:3.11-slim

# Install build dependencies for C-extensions (tgcrypto, pymongo, etc.)
RUN apt-get update && apt-get install -y \
      build-essential \
      python3-dev \
      libffi-dev \
      libssl-dev \
      libgmp-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies from requirements.txt (no-cache-dir to slim image)
COPY requirements.txt . 
RUN pip install --no-cache-dir -r requirements.txt

# (Optional) Environment/Port for Koyeb health check
ENV PORT 8080
EXPOSE $PORT

# Copy the bot source code into the image
COPY . /app

# Start the bot and Flask web server together
CMD ["python", "web_and_bot.py"]
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "--bind", ":8080", "--workers", "2", "web_and_bot:app"]
