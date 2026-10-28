FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    TOKENIZERS_PARALLELISM=false \
    FASTEMBED_CACHE_PATH=/opt/autosaarthi/fastembed

RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr libgomp1 gosu \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

# Bake the small ONNX model into the image so free instances don't download it
# into ephemeral storage on the first chat request after a restart.
RUN python -c "from fastembed import TextEmbedding; TextEmbedding(model_name='sentence-transformers/all-MiniLM-L6-v2', cache_dir='/opt/autosaarthi/fastembed', threads=1, enable_cpu_mem_arena=False)"

COPY . .
RUN useradd --create-home --shell /bin/bash autosaarthi \
    && mkdir -p /home/autosaarthi/.ssh /var/data \
    && chmod 700 /home/autosaarthi/.ssh \
    && chown -R autosaarthi:autosaarthi /home/autosaarthi /opt/autosaarthi \
    && chmod +x /app/render-entrypoint.sh

ENTRYPOINT ["/app/render-entrypoint.sh"]
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT:-10000} --workers 1 --threads 4 --timeout 600 app:app"]
