# ForeFlight Logbook Manager

A powerful tool for managing and analyzing ForeFlight logbook data. This application helps pilots organize, analyze, and visualize their flight data from ForeFlight.

## Features

- Import ForeFlight logbook data
- Analyze flight hours and patterns
- Generate reports and statistics
- Track currency requirements
- Visualize flight data

## Setup

1. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Unix/macOS
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
Create a `.env` file with your ForeFlight API credentials (if applicable).

## Project Structure

```
foreflight_logbook/
├── src/               # Source code
├── tests/            # Test files
├── docs/             # Documentation
├── venv/             # Virtual environment
├── requirements.txt  # Project dependencies
└── README.md         # This file
```

## Development

- Use `black` for code formatting
- Use `isort` for import sorting
- Use `flake8` for linting
- Write tests using `pytest`

## License

MIT License

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request 