FROM python:3.13-slim AS runtime

WORKDIR /app

COPY apps/backend/pyproject.toml /app/apps/backend/pyproject.toml
RUN pip install --no-cache-dir /app/apps/backend

COPY apps/backend /app/apps/backend

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "apps/backend"]
