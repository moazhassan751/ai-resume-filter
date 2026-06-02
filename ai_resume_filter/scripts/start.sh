#!/usr/bin/env bash
set -e

echo "=== TalentLens AI — Starting ==="

if [ ! -d "venv" ]; then
  echo "Virtual environment not found. Run scripts/setup.sh first."
  exit 1
fi

source venv/bin/activate
export PYTHONPATH="${PYTHONPATH}:$(pwd)/ai_resume_filter"

cd ai_resume_filter
python -m uvicorn app.main:app \
  --host "${HOST:-127.0.0.1}" \
  --port "${PORT:-8000}" \
  --reload