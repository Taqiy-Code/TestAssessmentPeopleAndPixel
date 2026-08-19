FROM python:3.12-slim

WORKDIR /app

# Install uv package manager
RUN pip install --no-cache-dir uv

# Copy dependency definition files
COPY pyproject.toml uv.lock ./

# Sync dependencies (this creates a .venv in /app/.venv by default)
RUN uv sync --no-dev

# Copy application source code
COPY app/ app/

EXPOSE 8000

# Run the FastAPI application using the python from the created virtual environment
CMD ["/app/.venv/bin/python", "-m", "app.main"]
