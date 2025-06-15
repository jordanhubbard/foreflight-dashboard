.PHONY: build build-dev build-prod build-test test test-cov format lint check clean docker-clean dev run init init-dev init-prod stop logs shell

# Default port for Flask UI
PORT ?= 5050

# Docker image and container names
IMAGE_NAME = foreflight-dashboard
CONTAINER_NAME = foreflight-dashboard

# Docker BuildKit settings
EXPORT_DOCKER_BUILDKIT = 1
BUILDKIT_PROGRESS ?= plain

# Python version
PYTHON_VERSION ?= 3.11

# Build tag
TAG ?= latest

# Ensure directories exist
setup:
	mkdir -p uploads logs

# Build the Docker image using Bake (development target)
build-dev: setup
	EXPORT_DOCKER_BUILDKIT=1 \
		BUILDKIT_PROGRESS=$(BUILDKIT_PROGRESS) \
		TAG=$(TAG) \
		PYTHON_VERSION=$(PYTHON_VERSION) \
		docker buildx bake development

# Build the Docker image using Bake (testing target)
build-test: setup
	EXPORT_DOCKER_BUILDKIT=1 \
		BUILDKIT_PROGRESS=$(BUILDKIT_PROGRESS) \
		TAG=$(TAG) \
		PYTHON_VERSION=$(PYTHON_VERSION) \
		docker buildx bake testing

# Build the Docker image using Bake (production target)
build-prod: setup
	EXPORT_DOCKER_BUILDKIT=1 \
		BUILDKIT_PROGRESS=$(BUILDKIT_PROGRESS) \
		TAG=$(TAG) \
		PYTHON_VERSION=$(PYTHON_VERSION) \
		docker buildx bake production

# Build all targets
build-all: setup
	EXPORT_DOCKER_BUILDKIT=1 \
		BUILDKIT_PROGRESS=$(BUILDKIT_PROGRESS) \
		TAG=$(TAG) \
		PYTHON_VERSION=$(PYTHON_VERSION) \
		docker buildx bake all

# Default build target (development)
build: build-dev

# Run tests in Docker using the dedicated test image
test: build-test
	docker run --rm \
		-v $(PWD)/tests:/app/tests \
		-v $(PWD)/logs:/app/logs \
		$(IMAGE_NAME):test pytest tests/

# Run tests with coverage
test-cov: build-test
	docker run --rm \
		-v $(PWD)/tests:/app/tests \
		-v $(PWD)/logs:/app/logs \
		-v $(PWD)/.coverage:/app/.coverage \
		$(IMAGE_NAME):test \
		pytest tests/ --cov=src -v

# Format code in Docker
format: build-dev
	docker run --rm \
		-v $(PWD)/src:/app/src \
		-v $(PWD)/tests:/app/tests \
		$(IMAGE_NAME):dev \
		sh -c "black src/ tests/ && isort src/ tests/"

# Lint code in Docker
lint: build-dev
	docker run --rm \
		-v $(PWD)/src:/app/src \
		-v $(PWD)/tests:/app/tests \
		$(IMAGE_NAME):dev \
		sh -c "flake8 src/ tests/ && black --check src/ tests/ && isort --check-only src/ tests/"

# Run all checks
check: lint test

# Initialize database (development)
init-dev: build-dev
	docker run --rm \
		-v $(PWD)/uploads:/app/uploads \
		-v $(PWD)/logs:/app/logs \
		$(IMAGE_NAME):dev \
		python -m src.db.init

# Initialize database (production)
init-prod: build-prod
	docker run --rm \
		-v $(PWD)/uploads:/app/uploads \
		-v $(PWD)/logs:/app/logs \
		$(IMAGE_NAME):prod \
		python -m src.db.init

# Default init target (development)
init: init-dev

# Development mode - containerized but runs in foreground (not daemonized)
dev: build-dev
	@echo "Starting development server in foreground..."
	@echo "Press Ctrl+C to stop the server"
	EXPORT_DOCKER_BUILDKIT=1 docker-compose up

# Production mode - containerized and runs in background (daemonized)
run: build-prod
	@echo "Starting production server in background..."
	EXPORT_DOCKER_BUILDKIT=1 docker-compose up -d
	@echo "Server started in background. Use 'make logs' to view logs or 'make stop' to stop."

# Stop the running container
stop:
	-docker-compose down 2>/dev/null || true
	-docker stop $(CONTAINER_NAME) 2>/dev/null || true
	-docker rm $(CONTAINER_NAME) 2>/dev/null || true
	@echo "Stop completed successfully"

# View logs from the container
logs:
	docker-compose logs -f 2>/dev/null || docker logs -f $(CONTAINER_NAME) 2>/dev/null || echo "No running containers found"

# Get a shell inside the container
shell: build-dev
	docker run --rm -it \
		-v $(PWD):/app \
		$(IMAGE_NAME):dev \
		/bin/bash

# Clean up project files
clean: docker-clean
	@-find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@-find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@-find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@-find . -type f -name "*.pyd" -delete 2>/dev/null || true
	@-find . -type f -name ".coverage" -delete 2>/dev/null || true
	@-find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@-find . -type d -name "*.egg" -exec rm -rf {} + 2>/dev/null || true
	@-find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@-find . -type d -name ".coverage" -exec rm -rf {} + 2>/dev/null || true
	@-find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	@-find . -type d -name "build" -exec rm -rf {} + 2>/dev/null || true
	@-find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	@-rm -f logs/* 2>/dev/null || true
	@-rm -f uploads/* 2>/dev/null || true
	@echo "Clean completed successfully"

# Clean Docker resources
docker-clean: stop
	@-docker rmi $(IMAGE_NAME):dev $(IMAGE_NAME):test $(IMAGE_NAME):prod $(IMAGE_NAME):latest-dev $(IMAGE_NAME):latest 2>/dev/null || true
	@echo "Docker clean completed successfully"

# Restart containers
restart: stop dev

# Legacy aliases for backward compatibility
start: run
