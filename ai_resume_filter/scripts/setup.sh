#!/usr/bin/env bash
set -e

echo "=== TalentLens AI — Setup ==="

# Create virtual environment
python -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r ai_resume_filter/requirements.txt

# Create required directories
mkdir -p data/{cache/tasks,models,vector_db/chroma,uploads,exports}

# Copy env template if needed
if [ ! -f ".env" ]; then
  cp .env.example .env 2>/dev/null || cat > .env << 'ENV'
SECRET_KEY=change-me-in-production
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB=talentlens
SKIP_HF_DATASET=0
MODEL_PATH=./data/models/model.pkl
VECTORIZER_PATH=./data/models/vectorizer.pkl
ENV
  echo "Created .env — update values before production use"
fi

echo "Setup complete. Next steps:"
echo "  1. source venv/bin/activate"
echo "  2. python scripts/normalize_datasets.py"
echo "  3. python scripts/data_pipeline.py"
echo "  4. python scripts/train_model.py"
echo "  5. python scripts/index_embeddings.py"
echo "  6. ./scripts/start.sh"