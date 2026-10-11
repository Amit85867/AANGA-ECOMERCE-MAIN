# AANGA backend — production image.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies first for layer caching. psycopg2-binary / Pillow ship wheels,
# so no system build toolchain is required.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render / Railway inject $PORT; default to 8000 for local `docker run`.
EXPOSE 8000
# gthread workers: a request spends most of its time waiting on Postgres or an
# upstream API, so a few threads per worker serve several of them at once
# without the memory of extra processes. Concurrent requests per worker (threads)
# must not exceed its connection pool (DB_POOL_SIZE + DB_MAX_OVERFLOW = 10).
# keep-alive is longer than a load balancer's idle timeout (typically 60 s): with
# gunicorn's default of 2 s the proxy reuses a connection the worker has just
# closed, and that request comes back to the visitor as a 502.
CMD ["sh", "-c", "gunicorn -b 0.0.0.0:${PORT:-8000} -k gthread -w ${WEB_CONCURRENCY:-2} --threads ${GUNICORN_THREADS:-4} --timeout 60 --graceful-timeout 30 --keep-alive ${GUNICORN_KEEPALIVE:-75} --access-logfile - run:app"]
