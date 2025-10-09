# Automata

## Installation

1. Ensure you have Python 3.9 or higher installed.
2. Install `uv` (a fast Python package installer):
   ```bash
   pip install uv
   ```
3. Clone the repository and navigate to the project directory.
4. Install dependencies using uv:
   ```bash
   uv sync
   ```
5. Activate the virtual environment:
   ```bash
   # On Windows
   .venv\Scripts\activate
   # On macOS/Linux
   source .venv/bin/activate
   ```

## Usage

### Running the Backend

Start the main application:
```bash
python main.py
```

The dashboard will be available at http://localhost:8080.

## Development

### Code Quality

This project uses the following tools for code quality:

- **Ruff**: Fast Python linter and formatter
- **Mypy**: Static type checker

### Running Checks

Install development dependencies:
```bash
uv sync --dev
```

Run linting and formatting:
```bash
uv run ruff check .
uv run ruff format .
```

Run type checking:
```bash
uv run mypy .
```

### Pre-commit Hooks (Optional)

You can set up pre-commit hooks to run these checks automatically:

```bash
pip install pre-commit
pre-commit install
```

The project includes a `.pre-commit-config.yaml` file with:
- Ruff linting and formatting
- MyPy type checking (using uv)
- Standard pre-commit hooks for code quality
