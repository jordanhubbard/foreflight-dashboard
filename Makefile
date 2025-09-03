# ForeFlight Dashboard Makefile
# Simplified Docker-based workflow with just three essential commands

# Variables
IMAGE_NAME=foreflight-dashboard
CONTAINER_NAME=foreflight-dashboard-container
COMPOSE_FILE=docker-compose.yml

# Default target
.PHONY: help test
help:
	@echo "ForeFlight Dashboard - Available Commands:"
	@echo ""
	@echo "  start        - Build and start the complete application"
	@echo "  stop         - Stop the running application"
	@echo "  clean        - Stop, remove container, and clean up images"
	@echo "  test         - Run all tests with coverage reporting"
	@echo ""
	@echo "Usage:"
	@echo "  make start   # First time setup and run"
	@echo "  make stop    # Stop the application"
	@echo "  make clean   # Complete cleanup"
	@echo "  make test    # Run tests with coverage"

# Start the application - builds everything and runs the container
.PHONY: start
start:
	@echo "🚀 Starting ForeFlight Dashboard..."
	@echo "Building and starting services with docker-compose..."
	docker-compose -f $(COMPOSE_FILE) build
	docker-compose -f $(COMPOSE_FILE) up -d
	@echo "Initializing database with default users..."
	docker-compose -f $(COMPOSE_FILE) exec foreflight-dashboard python src/init_db.py
	@echo "✅ Application started successfully!"
	@echo "🌐 Web UI: http://localhost:8081"
	@echo "🔧 API: http://localhost:5051"
	@echo "⚛️  React Dev: http://localhost:3000"
	@echo ""
	@echo "To view logs: docker-compose -f $(COMPOSE_FILE) logs -f"
	@echo "To stop: make stop"

# Stop the running application
.PHONY: stop
stop:
	@echo "🛑 Stopping ForeFlight Dashboard..."
	-docker-compose -f $(COMPOSE_FILE) down 2>/dev/null || true
	@echo "✅ Application stopped successfully!"

# Clean up everything - stop, remove container, and clean images
.PHONY: clean
clean: stop
	@echo "🧹 Cleaning up Docker resources..."
	-docker-compose -f $(COMPOSE_FILE) down -v --rmi all --remove-orphans 2>/dev/null || true
	-docker rmi $(IMAGE_NAME):latest 2>/dev/null || true
	-docker rmi $(IMAGE_NAME):dev 2>/dev/null || true
	-docker rmi $(IMAGE_NAME):prod 2>/dev/null || true
	-docker rmi $(IMAGE_NAME):test 2>/dev/null || true
	@echo "✅ Cleanup complete!"
	@echo ""
	@echo "To start fresh: make start"

# Run tests with coverage reporting
test:
	@echo "🧪 Running tests with coverage..."
	docker-compose -f $(COMPOSE_FILE) build
	docker-compose -f $(COMPOSE_FILE) run --rm foreflight-dashboard pytest tests/ -v --cov=src --cov-report=html --cov-report=term --cov-report=xml
	@echo "✅ Tests completed. Coverage report generated in htmlcov/"