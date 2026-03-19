FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN pip install --no-cache-dir .

CMD python scripts/run_migrations.py && uvicorn market_analyzer.server:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
