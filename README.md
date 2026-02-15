# benkthomp

Personal website built with Flask and deployed on Render.

## Project Structure

```
benkthomp/
├── src/
│   └── benkthomp/
│       ├── __init__.py
│       └── app.py
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── about.html
│   ├── projects.html
│   └── contact.html
├── static/
│   └── css/
│       └── style.css
├── tests/
│   ├── conftest.py
│   ├── test_unit.py
│   ├── test_integration.py
│   └── test_system.py
├── .gitignore
├── CHANGELOG.md
├── lint.py
├── pyproject.toml
├── render.yaml
└── README.md
```

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/ben-thomp/benkthomp.git
   cd benkthomp
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install in development mode**:
   ```bash
   pip install -e ".[dev]"
   ```

## Running the Application

```bash
python -m benkthomp.app
```

The application will be available at [http://localhost:5000](http://localhost:5000)

## Running Tests

```bash
pytest                              # All tests
pytest tests/test_unit.py           # Unit tests only
pytest tests/test_integration.py    # Integration tests only
pytest tests/test_system.py         # System tests only
```

## Code Quality

Run all checks (Black, Ruff, Mypy, and Pytest) with:

```bash
python lint.py
```

## Deployment

This project is configured for deployment on [Render](https://render.com) via `render.yaml`.

1. Push to GitHub
2. In Render, create a **New Blueprint Instance** and connect the repo
3. Render auto-detects `render.yaml` and deploys with Gunicorn

## Technology Stack

- **Backend**: Flask 3.0+
- **Testing**: pytest
- **Code Quality**: Black, Ruff, Mypy
- **Deployment**: Render with Gunicorn
