#!/bin/bash

echo "-----------------------------------------"
echo "Starting Recommendation Server"
echo "-----------------------------------------"

poetry run uvicorn market_analyzer.server:app --reload --host 0.0.0.0 --port 8000
