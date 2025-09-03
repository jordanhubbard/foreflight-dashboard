# ForeFlight Logbook Manager

[![CI/CD Pipeline](https://github.com/YOUR_USERNAME/foreflight-dashboard/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/foreflight-dashboard/actions/workflows/ci.yml)
[![Security Analysis](https://github.com/YOUR_USERNAME/foreflight-dashboard/actions/workflows/codeql.yml/badge.svg)](https://github.com/YOUR_USERNAME/foreflight-dashboard/actions/workflows/codeql.yml)
[![codecov](https://codecov.io/gh/YOUR_USERNAME/foreflight-dashboard/branch/main/graph/badge.svg)](https://codecov.io/gh/YOUR_USERNAME/foreflight-dashboard)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 18+](https://img.shields.io/badge/node.js-18+-green.svg)](https://nodejs.org/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)

A free, open-source tool for managing and analyzing ForeFlight logbook data. This application helps pilots organize, analyze, and visualize their flight data from ForeFlight. **This is not commercial software - no terms to agree to, completely free to use.**

## Features

- Import ForeFlight logbook data
- Analyze flight hours and patterns
- Generate reports and statistics
- Track currency requirements
- Visualize flight data

## Quick Start

### Prerequisites
- Docker
- make (optional, for simplified commands)

### Super Simple Setup

Just three commands to get everything running:

```bash
# Start the complete application (builds everything, installs dependencies, starts all services)
make start

# Stop the application
make stop

# Clean up everything (stops, removes containers, deletes images)
make clean
```

### What `make start` does:
1. **Builds** the Docker image with all dependencies (Python, Node.js, React, etc.)
2. **Initializes** the database with default users
3. **Starts** all services:
   - 🌐 **Web UI**: http://localhost:8081 (React frontend)
   - 🔧 **API**: http://localhost:5051 (FastAPI backend)
   - ⚛️ **React Dev**: http://localhost:3000 (Development server)

### Default Users
After running `make start`, you can log in with:
- **Admin**: `admin@example.com` / `admin`
- **User**: `user@example.com` / `user`
- **Student**: `student@example.com` / `student`

### GitHub Codespaces
1. Click the green "Code" button above
2. Select "Open with Codespaces"
3. Click "New codespace"
4. Run: `make start`
5. Access the forwarded port URL (typically port 8081)

### Manual Docker Commands

If you prefer not to use Make, you can run the Docker commands directly:

```bash
# Build the image
docker build --target development -t foreflight-dashboard:latest .

# Initialize database
docker run --rm \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/logs:/app/logs \
  foreflight-dashboard:latest \
  python src/init_db.py

# Start the application
docker run -d \
  --name foreflight-dashboard-container \
  -p 8081:8081 \
  -p 5051:5051 \
  -p 3000:3000 \
  -v $(pwd)/src:/app/src \
  -v $(pwd)/frontend:/app/frontend \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/logs:/app/logs \
  foreflight-dashboard:latest

# Stop the application
docker stop foreflight-dashboard-container
docker rm foreflight-dashboard-container

# Clean up
docker rmi foreflight-dashboard:latest
```

## Project Structure

```
foreflight-dashboard/
├── src/                    # Python backend source code
│   ├── app.py             # Flask application
│   ├── api/               # FastAPI routes
│   ├── core/              # Core models and security
│   ├── services/          # Business logic
│   └── templates/         # HTML templates
├── frontend/              # React frontend
│   ├── src/               # React source code
│   ├── package.json       # Node.js dependencies
│   └── vite.config.ts     # Vite configuration
├── tests/                 # Test files
├── uploads/               # User-uploaded files
├── logs/                  # Application logs
├── Dockerfile             # Multi-stage Docker build
├── docker-compose.yml     # Docker Compose configuration
├── Makefile              # Simplified build commands
└── requirements.txt       # Python dependencies
```

## Features

- **Modern React Frontend** with Material-UI design system
- **User Authentication** with Flask-Security-Too
- **Multi-user Support** with user-specific data isolation
- **File Upload** for ForeFlight CSV exports
- **Data Visualization** with charts and statistics
- **Student Pilot Features** including endorsement tracking
- **Responsive Design** that works on all devices
- **Professional UI** matching major tech companies

## Technology Stack

- **Backend**: Python 3.11, Flask, FastAPI, SQLAlchemy, Flask-Security-Too
- **Frontend**: React 18, TypeScript, Material-UI (MUI), Vite
- **Database**: SQLite (development), PostgreSQL (production ready)
- **Authentication**: Flask-Security-Too with bcrypt password hashing
- **Development**: Docker, Docker Compose, Hot reloading
- **Testing**: Pytest, React Testing Library, Vitest
- **CI/CD**: GitHub Actions, CodeQL Security Analysis, Automated Testing
- **Code Quality**: Black, Flake8, MyPy, ESLint, Prettier
- **Security**: Bandit, Safety, Trivy, SARIF reporting

## CI/CD Pipeline

This project includes a comprehensive CI/CD pipeline with:

### Continuous Integration
- **Multi-Python Testing**: Tests run on Python 3.9, 3.10, and 3.11
- **Code Quality Checks**: Black formatting, Flake8 linting, MyPy type checking
- **Security Scanning**: Bandit (Python), Safety (dependencies), Trivy (Docker)
- **Frontend Testing**: TypeScript compilation, ESLint, Vitest unit tests
- **Integration Tests**: Full application testing with Docker
- **Coverage Reporting**: Automated coverage reports with Codecov integration

### Security & Quality
- **CodeQL Analysis**: GitHub's semantic code analysis for security vulnerabilities
- **Dependency Updates**: Automated dependency updates with Renovate
- **Container Security**: Docker image vulnerability scanning
- **SARIF Integration**: Security findings integrated into GitHub Security tab

### Automated Workflows
- **Pull Request Checks**: All PRs automatically tested and validated
- **Release Management**: Automated releases with multi-platform Docker images
- **Performance Testing**: Basic load testing on main branch changes
- **Dependency Monitoring**: Weekly security scans and update notifications

### Running Tests Locally
```bash
# Run all tests with coverage
make test

# Run specific test categories
pytest tests/test_api/ -v          # API tests only
pytest tests/test_core/ -v         # Core functionality tests
pytest -m "not slow" tests/ -v     # Skip slow integration tests

# Frontend tests
cd frontend
npm test                           # Interactive test runner
npm run test:ci                    # CI mode with coverage
```

## License

MIT License

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request 