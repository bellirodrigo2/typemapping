.PHONY: install install_dev test lint format build clean

install:
	@echo "Instaling dependencies..."
	pip install .

install_dev:
	@echo "Instaling dev dependencies..."
	pip install .[dev]

test:
	@echo "Running tests..."
	pytest -p no:warnings -s 

test_coverage:
	@echo "Running tests with coverage..."
	pytest --cov=typemapping ./tests

test_cov_html:
	@echo "Running tests with html report coverage..."
	pytest --cov=typemapping ./tests --cov-report=html

lint:
	@echo "Running linter (ruff)..."
	ruff check .

lint_fix:
	@echo "Running linter --fix (ruff)..."
	ruff check --fix .

format:
	@echo "Formatting code (black e isort)..."
	black .
	isort .

build:
	@echo "Building package ..."
	python -m build

clean:
	@echo "Cleaning cache and build/dist related files..."
	@python -c "import shutil, glob, os; [shutil.rmtree(d, ignore_errors=True) for d in ['dist', 'build', '.mypy_cache', '.pytest_cache', '.ruff_cache'] + glob.glob('*.egg-info')]; [shutil.rmtree(os.path.join(r, d), ignore_errors=True) for r, ds, _ in os.walk('.') for d in ds if d == '__pycache__']"
