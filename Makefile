.PHONY: build test format lint check clean run run-dev stop logs shell

# Default port for Flask UI
PORT ?= 5050

# Docker image and container names
IMAGE_NAME = foreflight-dashboard
CONTAINER_NAME = foreflight-dashboard

# Ensure directories exist
setup:
	mkdir -p uploads logs

# Build the Docker image
build: setup
	docker build -t $(IMAGE_NAME) .

# Run tests in Docker
test: build
	docker run --rm \
		-v $(PWD)/tests:/app/tests \
		-v $(PWD)/logs:/app/logs \
		$(IMAGE_NAME) \
		pytest tests/ -v

# Format code in Docker
format: build
	docker run --rm \
		-v $(PWD)/src:/app/src \
		-v $(PWD)/tests:/app/tests \
		$(IMAGE_NAME) \
		sh -c "black src/ tests/ && isort src/ tests/"

# Lint code in Docker
lint: build
	docker run --rm \
		-v $(PWD)/src:/app/src \
		-v $(PWD)/tests:/app/tests \
		$(IMAGE_NAME) \
		sh -c "flake8 src/ tests/ && black --check src/ tests/ && isort --check-only src/ tests/"

# Run all checks
check: lint test

# Clean up project files
clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} +
	find . -type d -name "*.egg" -exec rm -r {} +
	find . -type d -name ".pytest_cache" -exec rm -r {} +
	find . -type d -name ".coverage" -exec rm -r {} +
	find . -type d -name "htmlcov" -exec rm -r {} +
	find . -type d -name "build" -exec rm -r {} +
	find . -type d -name "dist" -exec rm -r {} +
	rm -f logs/*
	rm -f uploads/*

# Clean Docker resources
docker-clean: stop
	docker rmi $(IMAGE_NAME) || true

# Run development mode with code reloading using docker-compose
run-dev: setup
	docker-compose up --build

# Run production mode
run: build
	docker run -d \
		--name $(CONTAINER_NAME) \
		-p $(PORT):5050 \
		-p 5051:5051 \
		-v $(PWD)/uploads:/app/uploads \
		-v $(PWD)/logs:/app/logs \
		--restart unless-stopped \
		$(IMAGE_NAME)

# Stop the running container
stop:
	docker stop $(CONTAINER_NAME) || true
	docker rm $(CONTAINER_NAME) || true

# View logs from the container
logs:
	docker logs -f $(CONTAINER_NAME)

# Get a shell inside the container
shell: build
	docker run --rm -it \
		-v $(PWD):/app \
		$(IMAGE_NAME) \
		/bin/bash
