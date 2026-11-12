FROM python:3.14.10-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY requirements.lock ./requirements.lock
RUN python -m pip install --require-hashes --no-cache-dir -r requirements.lock \
    && groupadd --system --gid 10001 cognova \
    && useradd --system --uid 10001 --gid cognova --no-create-home cognova

COPY --chown=10001:10001 app ./app
COPY --chown=10001:10001 scripts/start.py ./scripts/start.py

USER 10001:10001
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=5 \
  CMD python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/api/v1/health', timeout=2)"

CMD ["python", "scripts/start.py"]