# Backend image for Render (free-tier friendly). Lightweight: core deps only.
# For the full build with semantic dedup, swap requirements.txt -> requirements-full.txt
# and use a paid plan (PyTorch needs ~1 GB RAM).
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# libGL/glib keep Pillow + PyMuPDF happy on slim; no compiler needed (all wheels).
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# Render provides $PORT; default to 8000 for local runs.
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
