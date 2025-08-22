"""
Test configuration and fixtures
"""
import pytest
from fastapi.testclient import TestClient
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
