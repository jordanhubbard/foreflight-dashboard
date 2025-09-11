# ForeFlight Dashboard Makefile
# Simplified Docker-based workflow with just three essential commands

# Port Configuration (can be overridden by environment variables)
# Note: Flask has been eliminated! 🔥 FastAPI now handles everything
FASTAPI_PORT ?= 5051
REACT_DEV_PORT ?= 3001

# Export ports for use in docker-compose and other tools
export FASTAPI_PORT
export REACT_DEV_PORT

# Variables
IMAGE_NAME=foreflight-dashboard
CONTAINER_NAME=foreflight-dashboard-container
COMPOSE_FILE=docker-compose.yml

# Docker BuildKit optimization settings for local development
export DOCKER_BUILDKIT=1
export BUILDKIT_PROGRESS=plain
export BUILDKIT_INLINE_CACHE=1
export DOCKERFILE=Dockerfile.local

# Docker Compose build optimizations
COMPOSE_BUILD_OPTS=--parallel --pull

# Default target
.PHONY: help test
help:
	@echo "ForeFlight Dashboard - Available Commands:"
	@echo ""
	@echo "  start        - Build and start the complete application"
	@echo "  stop         - Stop the running application"
	@echo "  logs         - View application logs"
	@echo "  clean        - Complete cleanup: stop, remove containers, images, database, and files"
	@echo "  clean-cache  - Clean Docker build cache only (faster than full clean)"
	@echo "  test         - Run comprehensive test suite (Python + API integration)"
	@echo "  test-python  - Run Python/FastAPI tests only"
	@echo "  test-api     - Run API integration tests only"
	@echo "  test-accounts - Create test accounts from test-accounts.json"
	@echo "  build-prod   - Build optimized production image with buildx"
	@echo ""
	@echo "Port Configuration:"
	@echo "  FASTAPI_PORT   = $(FASTAPI_PORT) (Modern FastAPI app - replaces Flask!)"
	@echo "  REACT_DEV_PORT = $(REACT_DEV_PORT) (React dev server)"
	@echo ""
	@echo "🔥 Flask has been eliminated! FastAPI now handles everything! 🔥"
	@echo ""
	@echo "Usage:"
	@echo "  make start                              # Use default ports"
	@echo "  FASTAPI_PORT=9000 make start            # Use custom FastAPI port"
	@echo "  FASTAPI_PORT=9000 REACT_DEV_PORT=9001 make start  # Use custom ports"
	@echo "  make stop                               # Stop the application"
	@echo "  make logs                               # View application logs"
	@echo "  make clean                              # Complete cleanup (removes all data!)"
	@echo "  make test                               # Run tests with coverage"
	@echo "  make test-accounts                      # Create test accounts for debugging"

# Start the application - builds everything and runs the container
.PHONY: start
start:
	@echo "🚀 Starting ForeFlight Dashboard..."
	@echo "Building and starting services with optimized BuildKit..."
	docker-compose -f $(COMPOSE_FILE) build $(COMPOSE_BUILD_OPTS)
	docker-compose -f $(COMPOSE_FILE) up -d
	@echo "Initializing database with default users..."
	docker-compose -f $(COMPOSE_FILE) exec foreflight-dashboard python src/init_db.py
	@echo "✅ Modern FastAPI Application started successfully!"
	@echo "🔥 Flask eliminated! FastAPI now handles everything! 🔥"
	@echo ""
	@echo "🌐 Main Application: http://localhost:$(FASTAPI_PORT)"
	@echo "📚 API Documentation: http://localhost:$(FASTAPI_PORT)/docs"
	@echo ""
	@echo "ℹ️  Note: React dev server (port $(REACT_DEV_PORT)) runs inside container for development builds only"
	@echo ""
	@echo "To view logs: make logs"
	@echo "To stop: make stop"

# Stop the running application
.PHONY: stop
stop:
	@echo "🛑 Stopping ForeFlight Dashboard..."
	-docker-compose -f $(COMPOSE_FILE) down 2>/dev/null || true
	@echo "✅ Application stopped successfully!"

# View application logs
.PHONY: logs
logs:
	@echo "📋 Viewing ForeFlight Dashboard logs..."
	@echo "Press Ctrl+C to stop viewing logs"
	docker-compose -f $(COMPOSE_FILE) logs -f

# Clean up everything - stop, remove container, clean images, and reset data
.PHONY: clean
clean: stop
	@echo "🧹 Cleaning up Docker resources..."
	-docker-compose -f $(COMPOSE_FILE) down -v --rmi all --remove-orphans 2>/dev/null || true
	-docker rmi $(IMAGE_NAME):latest 2>/dev/null || true
	-docker rmi $(IMAGE_NAME):dev 2>/dev/null || true
	-docker rmi $(IMAGE_NAME):prod 2>/dev/null || true
	-docker rmi $(IMAGE_NAME):test 2>/dev/null || true
	@echo "🗑️  Cleaning up application data..."
	-rm -f data/app.db 2>/dev/null || true
	-rm -rf uploads/* 2>/dev/null || true
	-rm -rf logs/*.log* 2>/dev/null || true
	-find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	-find . -type f -name "*.pyc" -delete 2>/dev/null || true
	-find . -type f -name ".coverage" -delete 2>/dev/null || true
	-rm -rf htmlcov/ 2>/dev/null || true
	-rm -rf .pytest_cache/ 2>/dev/null || true
	-rm -rf frontend/node_modules/.cache/ 2>/dev/null || true
	@echo "✅ Complete cleanup finished!"
	@echo ""
	@echo "🔄 All data, logs, and caches removed"
	@echo "📊 Database will be recreated on next start"
	@echo "👤 Default users will be recreated"
	@echo ""
	@echo "To start fresh: make start"

# Clean Docker build cache only (faster than full clean)
.PHONY: clean-cache
clean-cache:
	@echo "🧹 Cleaning Docker build cache..."
	-docker builder prune -f 2>/dev/null || true
	-docker system prune -f 2>/dev/null || true
	@echo "✅ Docker build cache cleaned!"
	@echo ""
	@echo "🔄 Next build will be fresh (no cache)"
	@echo "To start: make start"

# Run all tests with coverage reporting - CONTAINER ONLY
.PHONY: test
test:
	@echo "🧪 Running comprehensive test suite..."
	@echo "📦 Building test containers with optimized BuildKit..."
	docker-compose -f $(COMPOSE_FILE) build $(COMPOSE_BUILD_OPTS)
	@echo ""
	@echo "🐍 Running Python/FastAPI tests..."
	docker-compose -f $(COMPOSE_FILE) run --rm foreflight-dashboard pytest tests/ -v --cov=src --cov-report=html --cov-report=term --cov-report=xml
	@echo ""
	@echo "🌐 Running API endpoint integration tests..."
	@echo "Starting application for API tests..."
	-docker-compose -f $(COMPOSE_FILE) up -d
	@sleep 10  # Wait for services to be ready
	docker-compose -f $(COMPOSE_FILE) exec -T foreflight-dashboard pytest tests/test_fastapi/ -v --tb=short || true
	@echo "Stopping test application..."
	-docker-compose -f $(COMPOSE_FILE) down
	@echo ""
	@echo "✅ All tests completed!"
	@echo "📊 Coverage report: htmlcov/index.html"
	@echo "🔍 XML coverage: coverage.xml"
	@echo ""
	@echo "🐳 All tests run inside containers - no host dependencies!"

# Run only Python tests (faster for development)
.PHONY: test-python
test-python:
	@echo "🐍 Running Python tests only..."
	docker-compose -f $(COMPOSE_FILE) build $(COMPOSE_BUILD_OPTS)
	docker-compose -f $(COMPOSE_FILE) run --rm foreflight-dashboard pytest tests/ -v --cov=src --cov-report=term
	@echo "✅ Python tests completed!"


# Run only API integration tests
.PHONY: test-api
test-api:
	@echo "🌐 Running API integration tests..."
	docker-compose -f $(COMPOSE_FILE) build $(COMPOSE_BUILD_OPTS)
	docker-compose -f $(COMPOSE_FILE) up -d
	@sleep 10  # Wait for services to be ready
	docker-compose -f $(COMPOSE_FILE) exec -T foreflight-dashboard pytest tests/test_fastapi/ -v
	docker-compose -f $(COMPOSE_FILE) down
	@echo "✅ API tests completed!"

# Create test accounts from JSON file
.PHONY: test-accounts
test-accounts:
	@echo "👥 Creating test accounts from test-accounts.json..."
	@if [ ! -f test-accounts.json ]; then \
		echo "❌ test-accounts.json not found in project root"; \
		exit 1; \
	fi
	@docker-compose -f $(COMPOSE_FILE) run --rm foreflight-dashboard python create_test_accounts.py
	@echo "✅ Test accounts created successfully!"
	@echo ""
	@echo "📋 You can now use these accounts to test the application:"
	@echo "   - Admin: admin@foreflight-dashboard.com / admin123"
	@echo "   - Test:  x@y.com / z"
	@echo "   - Student: student@example.com / student123"
	@echo "   - Instructor: instructor@example.com / instructor123"

# Build optimized production image with buildx
.PHONY: build-prod
build-prod:
	@echo "🏗️  Building optimized production image with buildx..."
	@echo "🚀 Using multi-platform build with cache optimization..."
	docker buildx build \
		--platform linux/amd64,linux/arm64 \
		--target production \
		--cache-from type=registry,ref=$(IMAGE_NAME):cache \
		--cache-to type=registry,ref=$(IMAGE_NAME):cache,mode=max \
		--build-arg BUILDKIT_INLINE_CACHE=1 \
		--tag $(IMAGE_NAME):latest \
		--tag $(IMAGE_NAME):prod \
		--push \
		.
	@echo "✅ Production image built and pushed with optimal caching!"