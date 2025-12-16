# syntax=docker/dockerfile:1
FROM python:3.12-slim

# ---- env ----
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1 \
    PATH="/root/.local/bin:$PATH"

# ---- system deps ----
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
  && rm -rf /var/lib/apt/lists/*

# ---- install uv ----
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

WORKDIR /app

# ---- install python deps (no editable install, no hatch build) ----
COPY pyproject.toml ./
RUN uv pip compile pyproject.toml -o requirements.txt \
 && uv pip install --system -r requirements.txt \
 && rm -f requirements.txt

# ---- copy app code ----
COPY . .

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
