.PHONY: install install_dev test lint format build clean test_cov_missing test_coverage lint_fix test_cov_py38  test_cov_py312 test_cov_combined

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

test_cov_missing:
	@echo "Running tests with missing report coverage..."
	pytest --cov=typemapping --cov-report=term-missing

test_cov_html:
	@echo "Running tests with html report coverage..."
	pytest --cov=typemapping ./tests --cov-report=html


# Run coverage for Python 3.8
test_cov_py38:
	@echo "Running coverage for Python 3.8..."
	@.venv38\Scripts\activate && coverage run --data-file=.coverage.py38 -m pytest --no-cov

# Run coverage for Python 3.12
test_cov_py312:
	@echo "Running coverage for Python 3.12..."
	@.venv\Scripts\activate && coverage run --data-file=.coverage.py312 -m pytest --no-cov

# Combine coverage from both Python versions
test_cov_combined:
	@echo "Running tests with coverage for Python 3.8..."
	@.venv38\Scripts\python -m coverage run --data-file=.coverage.py38 -m pytest --no-cov
	@echo ""
	@echo "Running tests with coverage for Python 3.12..."
	@.venv\Scripts\python -m coverage run --data-file=.coverage.py312 -m pytest --no-cov
	@echo ""
	@echo "Combining coverage data..."
	@coverage combine .coverage.py38 .coverage.py312
	@echo ""
	@echo "Combined coverage report:"
	@coverage report --show-missing
	@coverage html
	@echo ""
	@echo "HTML report generated in htmlcov/index.html"

# Clean coverage files
clean_coverage:
	@rm -f .coverage .coverage.* htmlcov

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

upload_pypi: build
	@echo "Uploading package to pypi ..."
	twine upload dist/*

clean:
	@echo "Cleaning cache and build/dist related files..."
	@python -c "import shutil, glob, os; [shutil.rmtree(d, ignore_errors=True) for d in ['dist', 'build', '.mypy_cache', '.pytest_cache', '.ruff_cache'] + glob.glob('*.egg-info')]; [shutil.rmtree(os.path.join(r, d), ignore_errors=True) for r, ds, _ in os.walk('.') for d in ds if d == '__pycache__']"
