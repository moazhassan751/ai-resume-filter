"""
Test configuration and fixtures
"""
import warnings

import pytest
from fastapi.testclient import TestClient
import os

# Ensure required env vars for config validation during tests
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("ALLOWED_HOSTS", '["localhost", "testserver"]')

warnings.filterwarnings(
    "ignore",
    message=r"Accessing the 'model_fields' attribute on the instance is deprecated.*",
)

from app.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def sample_resume_data():
    """Sample resume data for testing"""
    return {
        "name": "John Doe",
        "email": "john.doe@example.com",
        "skills": ["Python", "FastAPI", "Machine Learning"],
        "experience": "5 years",
        "education": "Computer Science Degree"
    }
