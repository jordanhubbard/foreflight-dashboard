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

### Using Make (Recommended)

1. Create a virtual environment and install dependencies:
```bash
make setup
```

2. Run the application:
```bash
make run
```

3. Clean up (optional):
```bash
make clean
```

### Manual Setup

1. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Unix/macOS
# or
.\venv\Scripts\activate  # On Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
flask run --port 5050
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

- `make setup` - Create virtual environment and install dependencies
- `make run` - Start the application
- `make clean` - Remove virtual environment and cached files
- `make test` - Run tests
- `make lint` - Run linting checks
- `make format` - Format code using black and isort

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