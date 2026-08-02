# Contributing to Vectoria

Thank you for your interest in contributing to Vectoria! This document provides guidelines and instructions for contributing.

## Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- Git

### Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/chintan1529/vectoria-semantic-search.git
   cd vectoria-semantic-search
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install frontend dependencies:**
   ```bash
   cd frontend && npm install && cd ..
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

5. **Build the index (first time only):**
   ```bash
   python build_index.py
   ```

6. **Start development servers:**
   ```bash
   # Terminal 1: Backend
   python -m uvicorn backend.api:app --reload --port 8000

   # Terminal 2: Frontend
   cd frontend && npm run dev
   ```

## Project Structure

```
vectoria/              # Core retrieval library
├── ingestion/         # Document loading & chunking
├── embedding/         # Sentence-transformer encoding
├── indexing/          # FAISS index management
├── retrieval/         # Search orchestration
└── evaluation/        # Metrics & benchmarking

backend/               # FastAPI backend
├── providers/         # LLM provider abstraction
├── orchestration/     # Generation & streaming
├── routes/            # API endpoints
└── core/              # Configuration

frontend/              # Next.js frontend
└── src/app/           # App Router pages

scripts/               # Utility scripts
docs/                  # Documentation
```

## Development Guidelines

### Code Style
- Python: Follow PEP 8. Use type hints for all function signatures.
- TypeScript: Follow the existing ESLint configuration.
- Use descriptive variable names and docstrings.

### Testing
```bash
# Run Python tests
pytest tests/

# Run evaluation suite
python scripts/run_competitive_benchmark.py
```

### Commit Messages
Use conventional commits:
- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `refactor:` Code restructuring
- `test:` Test additions/changes
- `chore:` Maintenance tasks

## Pull Request Process

1. Fork the repository and create a feature branch
2. Make your changes with appropriate tests
3. Ensure all existing tests pass
4. Update documentation if needed
5. Submit a PR with a clear description

## Reporting Issues

Please include:
- Steps to reproduce
- Expected vs actual behavior
- Python/Node.js version
- Operating system

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
