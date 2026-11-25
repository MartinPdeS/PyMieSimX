FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install --no-install-recommends -y libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

RUN python -m pip install --upgrade pip \
    && python -m pip install --no-cache-dir . \
    && python -m PyOptik setup --no-progress

EXPOSE 8050

CMD ["sh", "-c", "exec gunicorn PyMieSimX.application.wsgi:server --bind 0.0.0.0:${PORT:-8050} --workers 1 --threads 2 --timeout 3600"]
