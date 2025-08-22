# AI Resume Filter

An intelligent resume filtering and analysis system powered by AI and CrewAI agents.

## 🚀 Features

- **AI-Powered Resume Analysis**: Leverage advanced AI models to analyze and score resumes
- **CrewAI Integration**: Multi-agent system for comprehensive resume evaluation
- **Vector Database**: Efficient resume storage and similarity search using ChromaDB
- **REST API**: FastAPI-based RESTful API for easy integration
- **File Upload Support**: Support for PDF, DOC, DOCX, and TXT resume formats
- **Batch Processing**: Analyze multiple resumes simultaneously
- **Export Capabilities**: Export analysis results in various formats

## 📁 Project Structure

```text
ai_resume_filter/
├── app/                     # Main application
│   ├── __init__.py
│   ├── main.py             # FastAPI entry point
│   ├── agents/             # CrewAI agents
│   ├── api/v1/             # API endpoints
│   ├── core/               # Core functionality
│   │   └── config.py       # Configuration
│   ├── models/             # Database models
│   ├── schemas/            # Pydantic schemas  
│   ├── services/           # Business logic
│   └── utils/              # Utilities
├── data/                   # Data storage
│   ├── uploads/            # Resume uploads
│   ├── vector_db/chroma/   # Vector database
│   └── exports/            # Data exports
├── tests/                  # Tests
│   ├── conftest.py         
│   └── test_main.py        
├── scripts/                # Utility scripts
│   ├── start.sh
│   └── setup.sh
├── requirements.txt        # Dependencies
├── .env.example           # Environment template
├── .gitignore             # Git exclusions
└── README.md              # Documentation
```

## 🛠️ Installation

### Prerequisites

- Python 3.8+
- Git

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/moazhassan751/ai-resume-filter.git
   cd ai-resume-filter
   ```

2. **Run the setup script** (Linux/Mac)
   ```bash
   chmod +x ai_resume_filter/scripts/setup.sh
   ./ai_resume_filter/scripts/setup.sh
   ```

3. **Manual setup** (Windows or alternative)
   ```bash
   # Create virtual environment
   python -m venv venv
   
   # Activate virtual environment
   # Windows
   venv\Scripts\activate
   # Linux/Mac
   source venv/bin/activate
   
   # Install dependencies
   pip install -r ai_resume_filter/requirements.txt
   
   # Copy environment template
   copy ai_resume_filter\.env.example ai_resume_filter\.env  # Windows
   cp ai_resume_filter/.env.example ai_resume_filter/.env    # Linux/Mac
   ```

4. **Configure environment variables**

   Edit `ai_resume_filter/.env` and add your API keys:

   ```env
   OPENAI_API_KEY=your-openai-api-key-here
   ANTHROPIC_API_KEY=your-anthropic-api-key-here
   SECRET_KEY=your-secret-key-change-this-in-production
   ```

## 🚀 Usage

### Starting the Application

**Using the start script** (Linux/Mac):

```bash
chmod +x ai_resume_filter/scripts/start.sh
./ai_resume_filter/scripts/start.sh
```

**Manual start**:

```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Start the application
cd ai_resume_filter
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The API will be available at: `http://127.0.0.1:8000`

### API Documentation

Once the application is running, you can access:

- **Interactive API docs**: `http://127.0.0.1:8000/docs`
- **ReDoc documentation**: `http://127.0.0.1:8000/redoc`

### Basic API Endpoints

- `GET /` - Root endpoint
- `GET /health` - Health check
- `GET /api/v1/` - API v1 root

## 🧪 Testing

Run the test suite:

```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Run tests
cd ai_resume_filter
pytest
```

## 🔧 Configuration

Configuration is managed through environment variables. Key settings include:

- `APP_NAME`: Application name
- `DEBUG`: Enable/disable debug mode
- `HOST` & `PORT`: Server host and port
- `SECRET_KEY`: Security key for sessions
- `DATABASE_URL`: Database connection string
- `OPENAI_API_KEY`: OpenAI API key for AI features
- `ANTHROPIC_API_KEY`: Anthropic API key for AI features
- `UPLOAD_DIR`: Directory for file uploads
- `MAX_FILE_SIZE`: Maximum file upload size

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- FastAPI for the excellent web framework
- CrewAI for the multi-agent system capabilities
- ChromaDB for vector database functionality
- OpenAI and Anthropic for AI model access
AI Resume Filter is an AI-powered recruitment tool that streamlines candidate evaluation with a Bubble.io frontend and FastAPI backend. Using CrewAI and Google Gemini, it parses resumes, matches jobs, detects biases, and generates scores
