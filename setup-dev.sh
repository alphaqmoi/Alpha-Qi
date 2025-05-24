#!/bin/bash

set -e

VENV_DIR="venv"

echo "🔍 Checking for Poetry..."
if command -v poetry &>/dev/null; then
    echo "📦 Poetry detected. Installing dependencies with Poetry..."
    poetry install
    poetry run pre-commit install
    poetry run pre-commit autoupdate
    echo "✅ Setup complete with Poetry!"
    exit 0
fi

# Check if WORKON_HOME is set (virtualenvwrapper)
if [[ -n "$WORKON_HOME" ]]; then
    echo "🌐 Detected virtualenvwrapper (WORKON_HOME=$WORKON_HOME)"
    echo "⚠️ Skipping virtual environment creation. Please activate your environment manually."
else
    if [[ ! -d "$VENV_DIR" ]]; then
        echo "🐍 Creating virtual environment in $VENV_DIR..."
        python3 -m venv "$VENV_DIR"
    else
        echo "📁 Using existing virtual environment: $VENV_DIR"
    fi

    # Activate venv
    source "$VENV_DIR/bin/activate"

    echo "📦 Installing requirements..."
    pip install -r requirements.txt
    pip install -r requirements-dev.txt

    echo "🧼 Installing pre-commit hooks..."
    pip install pre-commit
    pre-commit install
    pre-commit autoupdate

    echo "✅ Setup complete in venv!"
fi
