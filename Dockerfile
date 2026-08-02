# ─────────────────────────────────────────────
# Vectoria — Multi-stage Production Dockerfile
# ─────────────────────────────────────────────
# Stage 1: Build the Next.js frontend
# Stage 2: Assemble the Python backend + built frontend

# ── Stage 1: Frontend Build ──────────────────
FROM node:20-alpine AS frontend-build

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --production=false
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Backend + Serving ───────────────
FROM python:3.11-slim AS production

# System dependencies for FAISS, numpy, and sentence-transformers
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY vectoria/ ./vectoria/
COPY backend/ ./backend/
COPY scripts/ ./scripts/
COPY build_index.py ./
COPY docs/ ./docs/

# Copy storage artifacts (pre-built index)
COPY storage/ ./storage/

# Copy built frontend from stage 1
COPY --from=frontend-build /app/frontend/.next ./frontend/.next
COPY --from=frontend-build /app/frontend/public ./frontend/public
COPY --from=frontend-build /app/frontend/package.json ./frontend/package.json
COPY --from=frontend-build /app/frontend/node_modules ./frontend/node_modules

# Environment
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV NODE_ENV=production

# Expose ports (backend: 8000, frontend: 3000)
EXPOSE 8000 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Start script
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
