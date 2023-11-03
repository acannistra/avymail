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

COPY . /app
