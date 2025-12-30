# Multi-stage Dockerfile for Hugging Face Spaces

# Stage 1: Build Frontend
FROM node:18-alpine as frontend-builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: Python Backend
FROM python:3.11-slim

# Install system dependencies (if any needed for ReportLab or Pillow)
# libgl1-mesa-glx and libglib2.0-0 are often needed for OpenCV-like libs, 
# but ReportLab is usually pure python or needs standard zlib which is standard.
# We'll install minimal basics just in case.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create a user to avoid running as root (Good practice, often required by HF)
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

# Copy Python requirements
COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY --chown=user:user . .

# Copy built frontend from Stage 1
COPY --from=frontend-builder --chown=user:user /app/dist ./dist

# Expose port 7860 (Hugging Face default)
EXPOSE 7860

# Run the server
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "7860"]
