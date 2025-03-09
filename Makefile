.PHONY: install test format lint check clean run run-dev setup

install:
	. venv/bin/activate && pip install -r requirements.txt

test:
	. venv/bin/activate && pytest tests/ -v

format:
	. venv/bin/activate && black src/ tests/
	. venv/bin/activate && isort src/ tests/

lint:
	. venv/bin/activate && flake8 src/ tests/
	. venv/bin/activate && black --check src/ tests/
	. venv/bin/activate && isort --check-only src/ tests/

check: lint test

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

setup:
	python3 -m venv venv
	. venv/bin/activate && pip install --upgrade pip
	. venv/bin/activate && $(MAKE) install
	mkdir -p uploads

run-dev:
	. venv/bin/activate && PYTHONPATH=. FLASK_DEBUG=1 FLASK_ENV=development python3 src/app.py

run:
	. venv/bin/activate && PYTHONPATH=. python3 src/app.py
