# Contributing to Aizen

Thank you for your interest in contributing to Aizen! We welcome pull requests, bug reports, and feature requests.

## Development Environment Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/irtaza302/aizen-agent.git
   cd aizen-agent
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. **Install development dependencies:**
   ```bash
   pip install -e ".[dev]"
   ```

## Running Tests

Aizen uses `pytest` for testing. To run the test suite, ensure your virtual environment is activated and run:

```bash
python -m pytest tests/ -v
```

If you are adding new features, please add accompanying tests. We aim to keep our coverage high and edge cases well-documented.

## Code Style & Linting

Aizen uses `ruff` for fast linting and formatting, and `mypy` for static type checking.

1. **Run Ruff:**
   ```bash
   ruff check .
   ruff format .
   ```

2. **Run Mypy:**
   ```bash
   mypy aizen/
   ```

## Pull Request Guidelines
- Branch off the `main` branch.
- Keep PRs focused on a single issue or feature.
- Update `CHANGELOG.md` with your changes.
- Ensure all tests pass before requesting a review.
