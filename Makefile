PYTHON := .venv/bin/python
PIP := .venv/bin/pip

.PHONY: venv install dev-run clean

venv:
	python3 -m venv .venv && \
	$(PIP) install --upgrade pip

install: venv
	$(PIP) install -r requirements.txt

dev-run:
	. .venv/bin/activate && PULSE_SERVER=/mnt/wslg/PulseServer python -m src.main

clean:
	rm -rf .venv

