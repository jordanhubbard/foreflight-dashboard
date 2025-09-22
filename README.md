# ForeFlight Logbook Manager

[![CI/CD Pipeline](https://github.com/jordanhubbard/foreflight-dashboard/actions/workflows/ci.yml/badge.svg)](https://github.com/jordanhubbard/foreflight-dashboard/actions/workflows/ci.yml)
[![Security Analysis](https://github.com/jordanhubbard/foreflight-dashboard/actions/workflows/codeql.yml/badge.svg)](https://github.com/jordanhubbard/foreflight-dashboard/actions/workflows/codeql.yml)
[![codecov](https://codecov.io/gh/jordanhubbard/foreflight-dashboard/branch/main/graph/badge.svg)](https://codecov.io/gh/YOUR_USERNAME/foreflight-dashboard)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 18+](https://img.shields.io/badge/node.js-18+-green.svg)](https://nodejs.org/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)

A free, open-source tool for managing and analyzing ForeFlight logbook data. This application helps pilots organize, analyze, and visualize their flight data from ForeFlight. **This is not commercial software - no terms to agree to, completely free to use.**

🐳 **Container-First Architecture**: This application is designed exclusively for containerized deployment. All operations run inside Docker containers for consistency, security, and easy deployment to any container platform.

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

## 🚀 Production Deployment

This application is designed for **container-first deployment** and can be deployed on any platform that supports Docker containers. The application is fully self-contained and includes everything needed to run in production.

### 📋 Deployment Requirements

- **Container Runtime**: Docker or compatible (Podman, containerd)
- **Memory**: Minimum 512MB RAM (1GB+ recommended for production)
- **Storage**: 1GB+ for database and file uploads (persistent volume recommended)
- **Network**: Single port exposure (configurable, defaults to 3001 for UI)

### 🌍 Environment Variables

```bash
# Application Configuration
ENVIRONMENT=production         # Set to 'production' for production deployment
FASTAPI_PORT=5051             # FastAPI backend port (internal)
REACT_DEV_PORT=3001           # React frontend port (primary UI)
SECRET_KEY=your-secret-key    # JWT signing key (REQUIRED in production)

# Database Configuration (optional - defaults to SQLite)
DATABASE_URL=postgresql://user:pass@host:port/db
DB_PATH=/app/data/app.db      # SQLite database location

# File Storage
UPLOAD_PATH=/app/uploads      # File upload directory
DATA_PATH=/app/data          # Application data directory

# Security (Production)
ALLOWED_HOSTS=yourdomain.com,*.yourdomain.com  # Restrict host access
CORS_ORIGINS=https://yourdomain.com            # CORS allowed origins
```

### 🐳 Container Platforms

## 🚀 Railway.com (Recommended - Easiest)

**Free tier available, automatic HTTPS, custom domains**

1. **Fork this repository** to your GitHub account
2. **Connect to Railway**: Visit [railway.app](https://railway.app) and sign in with GitHub
3. **Deploy**: Click "New Project" → "Deploy from GitHub repo" → Select your fork
4. **Configure**:
   ```bash
   # Railway automatically detects the Dockerfile
   # Set these environment variables in Railway dashboard:
   ENVIRONMENT=production
   SECRET_KEY=your-random-secret-key-here
   ```
5. **Access**: Railway provides a public URL automatically

**Cost**: Free tier (500 hours/month), $5/month for unlimited

---

## 🌊 DigitalOcean App Platform

**Managed container hosting with built-in CI/CD**

1. **Create App**: Visit [DigitalOcean App Platform](https://cloud.digitalocean.com/apps)
2. **Connect Repository**: Link your GitHub repository
3. **Configure Build**:
   ```yaml
   # .do/app.yaml (create this file in your repo root)
   name: foreflight-dashboard
   services:
   - name: web
     source_dir: /
     github:
       repo: your-username/foreflight-dashboard
       branch: main
     dockerfile_path: Dockerfile
     http_port: 3001
     instance_count: 1
     instance_size_slug: basic-xxs
     environment_slug: node-js
     envs:
     - key: ENVIRONMENT
       value: production
     - key: SECRET_KEY
       value: your-secret-key
       type: SECRET
   ```
4. **Deploy**: DigitalOcean automatically builds and deploys

**Cost**: $5/month for basic plan

---

## 📦 Heroku Container Registry

**Traditional PaaS with container support**

1. **Install Heroku CLI** and login: `heroku login`
2. **Create App**:
   ```bash
   heroku create your-app-name
   heroku container:login
   ```
3. **Configure Environment**:
   ```bash
   heroku config:set ENVIRONMENT=production
   heroku config:set SECRET_KEY=$(openssl rand -base64 32)
   heroku config:set FASTAPI_PORT=$PORT
   ```
4. **Deploy**:
   ```bash
   heroku container:push web
   heroku container:release web
   ```

**Cost**: $7/month for basic dyno

---

## ☁️ AWS ECS/Fargate

**Scalable container service with AWS integration**

1. **Build and Push Image**:
   ```bash
   # Create ECR repository
   aws ecr create-repository --repository-name foreflight-dashboard
   
   # Get login token
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-east-1.amazonaws.com
   
   # Build and push
   docker build -t foreflight-dashboard .
   docker tag foreflight-dashboard:latest 123456789012.dkr.ecr.us-east-1.amazonaws.com/foreflight-dashboard:latest
   docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/foreflight-dashboard:latest
   ```

2. **Create ECS Task Definition**:
   ```json
   {
     "family": "foreflight-dashboard",
     "networkMode": "awsvpc",
     "requiresCompatibilities": ["FARGATE"],
     "cpu": "256",
     "memory": "512",
     "containerDefinitions": [
       {
         "name": "foreflight-dashboard",
         "image": "123456789012.dkr.ecr.us-east-1.amazonaws.com/foreflight-dashboard:latest",
         "portMappings": [
           {
             "containerPort": 3001,
             "protocol": "tcp"
           }
         ],
         "environment": [
           {"name": "ENVIRONMENT", "value": "production"},
           {"name": "SECRET_KEY", "value": "your-secret-key"}
         ]
       }
     ]
   }
   ```

3. **Create ECS Service** with Application Load Balancer

**Cost**: ~$15-30/month depending on usage

---

## 🏃 Google Cloud Run

**Serverless container platform, pay-per-use**

1. **Enable Cloud Run API** in Google Cloud Console
2. **Build and Deploy**:
   ```bash
   # Install gcloud CLI and authenticate
   gcloud auth login
   gcloud config set project your-project-id
   
   # Deploy directly from source
   gcloud run deploy foreflight-dashboard \
     --source . \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --port 3001 \
     --set-env-vars ENVIRONMENT=production,SECRET_KEY=your-secret-key
   ```

**Cost**: Pay-per-request, free tier available

---

## 🔷 Azure Container Instances

**Simple container hosting**

1. **Create Resource Group**:
   ```bash
   az group create --name foreflight-rg --location eastus
   ```

2. **Deploy Container**:
   ```bash
   az container create \
     --resource-group foreflight-rg \
     --name foreflight-dashboard \
     --image your-registry/foreflight-dashboard:latest \
     --ports 3001 \
     --environment-variables ENVIRONMENT=production SECRET_KEY=your-secret-key \
     --cpu 1 \
     --memory 1
   ```

**Cost**: ~$10-20/month for basic configuration

---

## 🏠 Self-Hosted (VPS/Dedicated Server)

**Full control, any VPS provider (Linode, Vultr, etc.)**

1. **Server Setup** (Ubuntu/Debian):
   ```bash
   # Install Docker
   curl -fsSL https://get.docker.com -o get-docker.sh
   sh get-docker.sh
   sudo usermod -aG docker $USER
   
   # Install Docker Compose
   sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
   sudo chmod +x /usr/local/bin/docker-compose
   ```

2. **Deploy Application**:
   ```bash
   # Clone repository
   git clone https://github.com/your-username/foreflight-dashboard.git
   cd foreflight-dashboard
   
   # Create production environment file
   cat > .env.production << EOF
   ENVIRONMENT=production
   SECRET_KEY=$(openssl rand -base64 32)
   FASTAPI_PORT=5051
   REACT_DEV_PORT=3001
   EOF
   
   # Deploy with Docker Compose
   docker-compose -f docker-compose.yml --env-file .env.production up -d
   ```

3. **Setup Reverse Proxy** (Nginx):
   ```nginx
   server {
       listen 80;
       server_name yourdomain.com;
       
       location / {
           proxy_pass http://localhost:3001;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

4. **SSL Certificate** (Let's Encrypt):
   ```bash
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d yourdomain.com
   ```

**Cost**: $5-20/month depending on VPS provider

---

### 🔒 Production Security Checklist

- [ ] Set `ENVIRONMENT=production`
- [ ] Generate strong `SECRET_KEY` (32+ random characters)
- [ ] Configure `ALLOWED_HOSTS` for your domain
- [ ] Set up HTTPS/SSL certificates
- [ ] Configure `CORS_ORIGINS` for your domain
- [ ] Use persistent volumes for data storage
- [ ] Set up automated backups
- [ ] Monitor application logs
- [ ] Configure health checks
- [ ] Set up monitoring/alerting

### 📊 Monitoring & Health Checks

All deployments include built-in health monitoring:

- **Health Check Endpoint**: `GET /health`
- **API Documentation**: `GET /api/docs`
- **Application Logs**: Available in container logs
- **Metrics**: Basic performance metrics available

### 🔄 Updates & Maintenance

**Automated Updates** (recommended):
```bash
# Set up GitHub Actions for automatic deployment
# See .github/workflows/deploy.yml for examples
```

**Manual Updates**:
```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose up --build -d
```

### 💾 Data Persistence

**Important**: Configure persistent storage for production:

```yaml
# docker-compose.override.yml for production
version: '3.8'
services:
  foreflight-dashboard:
    volumes:
      - ./data:/app/data          # Database persistence
      - ./uploads:/app/uploads    # File upload persistence
```

### 🆘 Troubleshooting

**Common Issues**:

1. **Port Conflicts**: Ensure ports 3001 and 5051 are available
2. **Memory Issues**: Increase container memory to 1GB+
3. **Database Permissions**: Ensure write permissions for `/app/data`
4. **File Upload Issues**: Ensure write permissions for `/app/uploads`

**Debug Mode**:
```bash
# Enable debug logging
docker-compose exec foreflight-dashboard tail -f /app/logs/foreflight.log
```

**Getting Help**:
- Check the [GitHub Issues](https://github.com/your-username/foreflight-dashboard/issues)
- Review container logs: `docker-compose logs -f`
- Verify health check: `curl http://localhost:3001/health`

## License

MIT License

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request 
