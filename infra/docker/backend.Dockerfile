FROM python:3.13-slim AS runtime

WORKDIR /app

ARG PIP_INDEX_URL=https://pypi.org/simple
ARG PIP_TRUSTED_HOST=
ENV PIP_INDEX_URL=$PIP_INDEX_URL
ENV PIP_TRUSTED_HOST=$PIP_TRUSTED_HOST
ENV PIP_DEFAULT_TIMEOUT=120

COPY apps/backend/pyproject.toml /app/apps/backend/pyproject.toml
RUN pip install --no-cache-dir /app/apps/backend

COPY apps/backend /app/apps/backend
COPY ai /app/ai
COPY packages/protocol/src/material-upload-formats.json /app/packages/protocol/src/material-upload-formats.json

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "apps/backend"]
