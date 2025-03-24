.PHONY: setup run clean service-install service-remove service-start service-stop

# Default port for Flask app
PORT ?= 5050

setup: venv
	mkdir -p logs

venv:
	python3 -m venv venv
	. venv/bin/activate && pip install --upgrade pip
	. venv/bin/activate && pip install -r requirements.txt

clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	rm -f logs/*
	rm -rf venv

run: setup
	. venv/bin/activate && \
	FLASK_APP=app.py \
	FLASK_DEBUG=1 \
	FLASK_ENV=development \
	PYTHONPATH=. \
	python3 -m flask run --host=0.0.0.0 --port=$(PORT) --reload

# Service management targets
service-install:
	sudo cp weather-forecasts.service /etc/systemd/system/
	sudo systemctl daemon-reload
	sudo systemctl enable weather-forecasts.service

service-remove:
	sudo systemctl disable weather-forecasts.service
	sudo rm /etc/systemd/system/weather-forecasts.service
	sudo systemctl daemon-reload

service-start:
	sudo systemctl start weather-forecasts.service

service-stop:
	sudo systemctl stop weather-forecasts.service
