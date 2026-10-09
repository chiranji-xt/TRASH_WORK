FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libpq5 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# CPU-only torch (~200MB) instead of the CUDA stack (~2.5GB of nvidia wheels).
# Inference runs on CPU; must come first so ultralytics' torch>=1.8.0
# requirement is already satisfied and pip doesn't fetch CUDA torch.
# Cache mount survives retries on flaky connections.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --timeout 300 --retries 10 \
    --index-url https://download.pytorch.org/whl/cpu torch torchvision

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --timeout 300 --retries 10 -r requirements.txt

COPY . .

CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
