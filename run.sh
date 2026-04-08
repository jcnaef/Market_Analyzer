#!/bin/bash

echo "-----------------------------------------"
echo "Starting Recommendation Server"
echo "-----------------------------------------"

# Single worker required: in-memory rate limiting state is not shared across workers
PYTHONUNBUFFERED=1 poetry run uvicorn market_analyzer.server:app --reload --host 0.0.0.0 --port 8000 --log-level info
