#!/bin/bash

# AI Resume Filter - Start Script

echo "Starting AI Resume Filter..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Please run setup.sh first."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Set environment variables
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Start the application
cd ai_resume_filter
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
