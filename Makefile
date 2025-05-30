.PHONY: build build-dev build-prod test format lint check clean run run-dev stop logs shell

# Default port for Flask UI
PORT ?= 5050

# Docker image and container names
IMAGE_NAME = foreflight-dashboard
CONTAINER_NAME = foreflight-dashboard

# Docker BuildKit settings
EXPORT_DOCKER_BUILDKIT = 1

# Ensure directories exist
setup:
	mkdir -p uploads logs

# Build the Docker image using Bake (development target)
build-dev: setup
	BUILDKIT_PROGRESS=plain docker buildx bake dev

# Build the Docker image using Bake (production target)
build-prod: setup
	BUILDKIT_PROGRESS=plain docker buildx bake prod

# Default build target (development)
build: build-dev

# Run tests in Docker
test: build-dev
	docker run --rm \
		-v $(PWD)/tests:/app/tests \
		-v $(PWD)/logs:/app/logs \
		$(IMAGE_NAME):latest-dev \
		pytest tests/ -v

# Run tests with coverage
test-cov: build-dev
	docker run --rm \
		-v $(PWD)/tests:/app/tests \
		-v $(PWD)/logs:/app/logs \
		-v $(PWD)/.coverage:/app/.coverage \
		$(IMAGE_NAME):latest-dev \
		pytest tests/ --cov=src -v

# Format code in Docker
format: build-dev
	docker run --rm \
		-v $(PWD)/src:/app/src \
		-v $(PWD)/tests:/app/tests \
		$(IMAGE_NAME):latest-dev \
		sh -c "black src/ tests/ && isort src/ tests/"

# Lint code in Docker
lint: build-dev
	docker run --rm \
		-v $(PWD)/src:/app/src \
		-v $(PWD)/tests:/app/tests \
		$(IMAGE_NAME):latest-dev \
		sh -c "flake8 src/ tests/ && black --check src/ tests/ && isort --check-only src/ tests/"

# Run all checks
check: lint test

# Clean Docker resources
clean: stop
	docker rmi $(IMAGE_NAME):latest-dev $(IMAGE_NAME):latest || true

# Run development mode with code reloading using docker-compose
run-dev: build-dev
	EXPORT_DOCKER_BUILDKIT=1 docker-compose up

# Run production mode
run: build-prod
	docker run -d \
		--name $(CONTAINER_NAME) \
		-p $(PORT):5050 \
		-p 5051:5051 \
		-v $(PWD)/uploads:/app/uploads \
		-v $(PWD)/logs:/app/logs \
		--restart unless-stopped \
		$(IMAGE_NAME):latest

# Stop the running container
stop:
	docker-compose down || true
	docker stop $(CONTAINER_NAME) || true
	docker rm $(CONTAINER_NAME) || true

# View logs from the container
logs:
	docker logs -f $(CONTAINER_NAME)

# Get a shell inside the container
shell: build-dev
	docker run --rm -it \
		-v $(PWD):/app \
		$(IMAGE_NAME):latest-dev \
		/bin/bash
