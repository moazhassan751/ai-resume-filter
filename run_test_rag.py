import sys
from pathlib import Path

# Ensure package path
sys.path.insert(0, str(Path(__file__).resolve().parent / "ai_resume_filter"))
import os
os.environ.setdefault("SECRET_KEY", "test-secret")
from app.main import app
from fastapi.testclient import TestClient
from app.api.deps import get_current_user
from types import SimpleNamespace

client = TestClient(app)
app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(email='t')
res = client.post('/api/v1/rag/analyze', json={'job_description':'Software engineer','top_k':5})
print('STATUS', res.status_code)
print(res.text)
