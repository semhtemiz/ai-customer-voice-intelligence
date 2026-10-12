FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY backend/requirements-runtime.txt /app/backend/requirements-runtime.txt
RUN pip install --no-cache-dir -r backend/requirements-runtime.txt
COPY backend/app /app/backend/app
COPY backend/scripts /app/backend/scripts
COPY backend/sql /app/backend/sql
COPY scripts/profile_dataset.py /app/scripts/profile_dataset.py
COPY backend/__init__.py /app/backend/__init__.py
COPY backend/docker-entrypoint.py /app/backend/docker-entrypoint.py
EXPOSE 8000
CMD ["python", "backend/docker-entrypoint.py"]
