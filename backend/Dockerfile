FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd -r app && useradd -r -g app app

COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install .

COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./alembic.ini

RUN chown -R app:app /app
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)" || exit 1

CMD ["sh", "-c", "exec gunicorn app.main:app --bind 0.0.0.0:8000 --worker-class uvicorn.workers.UvicornWorker --workers ${WEB_CONCURRENCY:-2} --timeout ${GUNICORN_TIMEOUT:-60} --graceful-timeout ${GUNICORN_GRACEFUL_TIMEOUT:-30} --keep-alive ${GUNICORN_KEEPALIVE:-5} --max-requests ${GUNICORN_MAX_REQUESTS:-1000} --max-requests-jitter ${GUNICORN_MAX_REQUESTS_JITTER:-100}"]
