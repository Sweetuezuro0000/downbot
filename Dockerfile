# Python 3.10 slim base image (lightweight)
FROM python:3.10-slim

# System update aur FFmpeg + Git install karein (yt-dlp ke liye zaroori hai)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Working directory set karein
WORKDIR /app

# Requirements file copy aur install karein (Layer caching ke liye)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Aapka poora project code copy karein
COPY . .

# Render ke port requirement ke liye environment variable
ENV PORT=8080
EXPOSE 8080

# Bot start karne ka command
CMD ["python", "main.py"]
