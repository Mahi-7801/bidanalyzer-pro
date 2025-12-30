# ==============================
# Stage 1: Build Frontend
# ==============================
FROM node:18-alpine AS frontend-builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# ==============================
# Stage 2: Backend (HF Space)
# ==============================
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy backend
COPY . .

# Copy frontend build
COPY --from=frontend-builder /app/dist ./dist

# Hugging Face default port
EXPOSE 7860

# Start FastAPI
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "7860"]
