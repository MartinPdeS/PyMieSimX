FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY . .

RUN python -m pip install --upgrade pip \
    && python -m pip install --no-cache-dir .

CMD ["sh", "-c", "exec gunicorn PyMieSimX.gui.interface:app --bind 0.0.0.0:${PORT:-8050} --workers 1 --threads 2 --timeout 3600"]
