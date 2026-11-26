# Makefile for Image Converter (Python + PySide6)
#
# Usage:
#   make install      create .venv and install the app dependencies
#   make run          install if needed, then start the app
#   make test         install dev tools and run the build test
#   make local-build  build the executable the same way as CI
#   make clean        remove caches, build folders and .venv

# Python used to create the virtual environment.
# Windows uses "python"; Linux uses "python3". Override with PYTHON=... if needed.
ifeq ($(OS),Windows_NT)
PYTHON ?= python
BIN_DIR := .venv/Scripts
else
PYTHON ?= python3
BIN_DIR := .venv/bin
endif

VENV := .venv
PY   := $(BIN_DIR)/python

# Marker file, updated only after the app dependencies finish installing.
STAMP := $(VENV)/.installed

.DEFAULT_GOAL := help
.PHONY: help install run test local-build clean

# Show the list of commands.
help:
	@echo "Targets:"
	@echo "  make install      create .venv and install the app dependencies"
	@echo "  make run          start the app"
	@echo "  make test         install dev tools and run the build test"
	@echo "  make local-build  build the executable the same way as CI"
	@echo "  make clean        remove caches, build folders and .venv"

# Create the virtual environment if it does not exist yet.
$(PY):
	$(PYTHON) -m venv $(VENV)

# Install app dependencies again only when requirements.txt changes.
$(STAMP): requirements.txt | $(PY)
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r requirements.txt
	$(PY) -c "import pathlib; pathlib.Path('$@').touch()"

# Create the environment and install the app dependencies.
install: $(STAMP)

# Start the GUI.
run: $(STAMP)
	$(PY) main.py

# Install the dev tools (pytest, PyInstaller) and run the build test.
test: $(STAMP)
	$(PY) -m pip install -q -r requirements-dev.txt pyinstaller
	$(PY) -m pytest tests/test_build.py -v

# Build the executable with the same steps as CI. Does not run the tests.
local-build: $(STAMP)
	$(PY) -m pip install -q pyinstaller
	$(PY) -m PyInstaller --noconfirm --onefile --windowed \
		--name image-converter --hidden-import pillow_jxl main.py
	@echo "Build concluído: dist/image-converter"
	@echo "Para abrir: ./dist/image-converter"

# Remove caches, build output and the virtual environment.
clean:
	$(PYTHON) -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]; [shutil.rmtree(d, ignore_errors=True) for d in ('build', 'dist', '.pytest_cache', '.venv')]; pathlib.Path('image-converter.spec').unlink(missing_ok=True)"
