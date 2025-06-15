# ForeFlight Logbook Manager

A powerful tool for managing and analyzing ForeFlight logbook data. This application helps pilots organize, analyze, and visualize their flight data from ForeFlight.

## Features

- Import ForeFlight logbook data
- Analyze flight hours and patterns
- Generate reports and statistics
- Track currency requirements
- Visualize flight data

## Quick Start with GitHub Codespaces

1. Click the green "Code" button above
2. Select "Open with Codespaces"
3. Click "New codespace"
4. Once the environment is ready, run:
```bash
make run
```

The application will be available at the forwarded port URL that GitHub Codespaces provides (typically port 5050).

## Local Setup

### Prerequisites
- Docker
- Docker Compose
- make (for using the Makefile commands)

### Containerized Setup (Recommended)

All operations are performed in Docker containers - no local Python installation needed.

1. Build and run the application:
```bash
make run
```

2. Access the application at http://localhost:5050

3. Clean up (optional):
```bash
make clean
```

### Manual Docker Commands

If you prefer not to use Make:

1. Build the development image:
```bash
docker buildx bake development
```

2. Run with docker-compose:
```bash
docker-compose up
```

## Project Structure

```
foreflight_logbook/
├── .devcontainer/    # GitHub Codespaces configuration
├── src/             # Source code
├── tests/           # Test files
├── logs/            # Application logs
├── uploads/         # Uploaded logbook files
├── Makefile        # Build automation
├── requirements.txt # Project dependencies
└── README.md       # This file
```

## Development

### Available Make Commands

- `make build-dev` - Build development Docker image
- `make build-prod` - Build production Docker image
- `make run` - Start the application with docker-compose
- `make test` - Run tests in Docker container
- `make lint` - Run linting checks in Docker container
- `make format` - Format code using black and isort in Docker container
- `make shell` - Get a shell inside the development container
- `make clean` - Remove Docker images and cached files
- `make stop` - Stop running containers

### Code Quality

- Uses `black` for code formatting
- Uses `isort` for import sorting
- Uses `flake8` for linting
- Tests written using `pytest`

## License

MIT License

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request 