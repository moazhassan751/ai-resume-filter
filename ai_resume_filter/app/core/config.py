"""
Configuration settings for the AI Resume Filter application
"""
import os
from typing import List
from pydantic import BaseSettings


class Settings(BaseSettings):
    # Application settings
    APP_NAME: str = "AI Resume Filter"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    
    # Security
    SECRET_KEY: str = "your-secret-key-here"
    ALLOWED_HOSTS: List[str] = ["*"]
    
    # Database settings
    DATABASE_URL: str = "sqlite:///./ai_resume_filter.db"
    
    # Vector Database settings
    CHROMA_PERSIST_DIRECTORY: str = "./data/vector_db/chroma"
    
    # File upload settings
    UPLOAD_DIR: str = "./data/uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".doc", ".docx", ".txt"]
    
    # AI/ML settings
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    
    # CrewAI settings
    CREW_VERBOSE: bool = True
    
    # Export settings
    EXPORT_DIR: str = "./data/exports"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
