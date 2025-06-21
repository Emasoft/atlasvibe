#!/bin/bash
# Installation script for AtlasVibe
# This script builds and installs AtlasVibe using uv package manager

set -e

echo "==============================================="
echo "AtlasVibe Installation Script"
echo "==============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check Python version
log_info "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>/dev/null | cut -d' ' -f2 | cut -d'.' -f1,2)
if [[ ! "$PYTHON_VERSION" =~ ^3\.(11|12)$ ]]; then
    log_error "Python 3.11 or 3.12 is required. Found: $PYTHON_VERSION"
    log_info "You can install Python 3.11 with uv after installing uv"
    echo "Proceeding to install uv..."
fi

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    log_info "Installing uv package manager..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"

    # Add to shell profile
    if [[ "$SHELL" == *"zsh"* ]]; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
    else
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
    fi

    log_success "uv installed successfully"
else
    log_success "uv is already installed"
fi

# Install Python 3.11 if needed
log_info "Setting up Python environment..."
if ! uv python find 3.11 &> /dev/null; then
    log_info "Installing Python 3.11..."
    uv python install 3.11
fi

# Pin Python version for the project
uv python pin 3.11
log_success "Python 3.11 is ready"

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    log_error "Node.js is required but not found."
    echo "Please install Node.js from https://nodejs.org/"
    echo "Recommended: Node.js 20.x or higher"
    exit 1
fi
log_success "Node.js is installed"

# Check if pnpm is installed
if ! command -v pnpm &> /dev/null; then
    log_info "Installing pnpm..."
    npm install -g pnpm
    log_success "pnpm installed"
else
    log_success "pnpm is already installed"
fi

# Create virtual environment
log_info "Creating virtual environment..."
uv venv --python 3.11

# Activate virtual environment (for this script)
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    # Windows
    source .venv/Scripts/activate
else
    # Unix-like (macOS, Linux)
    source .venv/bin/activate
fi

# Install Python dependencies
log_info "Installing Python dependencies..."
uv sync --all-extras --dev
log_success "Python dependencies installed"

# Install Node.js dependencies
log_info "Installing Node.js dependencies..."
pnpm install
log_success "Node.js dependencies installed"

# Build the frontend
log_info "Building frontend..."
pnpm run build
log_success "Frontend built"

# Build the Electron app
log_info "Building Electron application..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    pnpm run electron-package:mac
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    # Windows
    pnpm run electron-package:win
else
    # Linux
    pnpm run electron-package:linux
fi
log_success "Electron application built"

# Build the Python package
log_info "Building Python package..."
uv build --wheel
uv build --sdist
log_success "Python package built"

# Install the package in development mode
log_info "Installing AtlasVibe..."
uv pip install -e .
log_success "AtlasVibe installed"

# Install pre-commit hooks (optional for users)
if [ -f .pre-commit-config.yaml ]; then
    log_info "Setting up pre-commit hooks (optional)..."
    uv pip install pre-commit
    pre-commit install || log_warning "Pre-commit hooks setup skipped"
fi

echo ""
echo "==============================================="
log_success "AtlasVibe installation complete!"
echo ""
echo "To activate the virtual environment:"
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    echo "  .venv\\Scripts\\activate"
else
    echo "  source .venv/bin/activate"
fi
echo ""
echo "You can now run:"
echo "  atlasvibe --help    # Show all commands"
echo "  atlasvibe run       # Run the full application"
echo "  atlasvibe server    # Run only the backend server"
echo "  atlasvibe ui        # Run only the UI"
echo "  atlasvibe init PATH # Create a new project"
echo ""
echo "For development:"
echo "  uv run python main.py --reload  # Backend with hot reload"
echo "  pnpm run dev                    # Frontend with hot reload"
echo "==============================================="
