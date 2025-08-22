#!/bin/bash

# AI Resume Filter - Setup Script

echo "Setting up AI Resume Filter..."

# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Create necessary directories
mkdir -p ai_resume_filter/data/uploads
mkdir -p ai_resume_filter/data/vector_db/chroma
mkdir -p ai_resume_filter/data/exports

# Copy environment template
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "Created .env file from template. Please update it with your configuration."
fi

echo "Setup complete! Run scripts/start.sh to start the application."
