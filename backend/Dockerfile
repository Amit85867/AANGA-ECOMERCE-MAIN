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
CMD ["sh", "-c", "gunicorn -b 0.0.0.0:${PORT:-8000} -w ${WEB_CONCURRENCY:-2} --timeout 60 run:app"]
