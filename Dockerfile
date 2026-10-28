FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr libgomp1 gosu \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

COPY . .
RUN useradd --create-home --shell /bin/bash autosaarthi \
    && mkdir -p /home/autosaarthi/.ssh /var/data \
    && chmod 700 /home/autosaarthi/.ssh \
    && chown -R autosaarthi:autosaarthi /home/autosaarthi \
    && chmod +x /app/render-entrypoint.sh

ENTRYPOINT ["/app/render-entrypoint.sh"]
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT:-10000} --workers 1 --threads 4 --timeout 600 app:app"]
