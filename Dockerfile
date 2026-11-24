FROM python:3.10 as reqs-build

WORKDIR /tmp

ENV POETRY_VERSION=1.7.0
RUN pip install --no-cache-dir --upgrade "poetry==$POETRY_VERSION"

COPY poetry.lock pyproject.toml /tmp
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes

FROM tiangolo/uvicorn-gunicorn-fastapi:python3.10

COPY --from=reqs-build /tmp/requirements.txt /app/requirements.txt

ENV PYTHONFAULTHANDLER=1 \
  PYTHONUNBUFFERED=1 \
  PYTHONHASHSEED=random \
  PIP_NO_CACHE_DIR=off \
  PIP_DISABLE_PIP_VERSION_CHECK=on \
  PIP_DEFAULT_TIMEOUT=100 \
  POETRY_VERSION=1.0.0 \
  APP_MODULE="api:app" \
  PORT=8080

WORKDIR /app

RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

# Supercronic runs send-avymail.py on the schedule in /app/crontab (the "cron" process in fly.toml).
ENV SUPERCRONIC_URL=https://github.com/aptible/supercronic/releases/download/v0.2.51/supercronic-linux-amd64 \
  SUPERCRONIC_SHA1SUM=1692066e350a88ff4d7d6474fe3c7a6c41ec5e89 \
  SUPERCRONIC=supercronic-linux-amd64

RUN curl -fsSLO "$SUPERCRONIC_URL" \
  && echo "${SUPERCRONIC_SHA1SUM}  ${SUPERCRONIC}" | sha1sum -c - \
  && chmod +x "$SUPERCRONIC" \
  && mv "$SUPERCRONIC" /usr/local/bin/supercronic

COPY . /app
