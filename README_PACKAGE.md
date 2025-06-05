# AtlasVibe Python Package

AtlasVibe is now distributed as a standard Python package that includes both the backend server and the Electron UI.

## Installation

### Option 1: Install from source (recommended for development)

```bash
# Clone the repository
git clone https://github.com/Emasoft/atlasvibe.git
cd atlasvibe

# Run the installation script
./install.sh
```

### Option 2: Install with pip (when published)

```bash
pip install atlasvibe
```

## Usage

After installation, you can use the `atlasvibe` command:

```bash
# Run the full application (server + UI)
atlasvibe

# Run only the backend server
atlasvibe server --port 5392 --log-level INFO

# Run only the UI
atlasvibe ui

# Run UI in development mode
atlasvibe ui --dev

# Initialize a new project
atlasvibe init my-project
```

## Development

### Running from source without installation

```bash
# Setup environment
uv venv --python 3.11
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv sync --all-extras

# Install Node dependencies
pnpm install

# Build frontend
pnpm run build

# Run the server
uv run python main.py

# In another terminal, run the UI
pnpm run dev
```

### Building the package

```bash
# Build the Python wheel
uv run python -m build

# The wheel will be in dist/
ls dist/
```

## Architecture Changes

### No More ASAR

The Electron app is no longer packaged as an ASAR archive. This simplifies:
- File access and path resolution
- Development and debugging
- Integration with Python code

### Unified Package

Everything is now in a single Python package:
- Python backend code
- Electron frontend (pre-built)
- Block libraries
- All dependencies managed through pip/uv

### Benefits

1. **Simple Installation**: Just `pip install atlasvibe`
2. **No Electron Builder**: No need for platform-specific builds
3. **Easy Distribution**: Standard Python package on PyPI
4. **Better Integration**: Python and JS code in same package
5. **Simplified Paths**: No more ASAR extraction issues

## File Structure

```
atlasvibe/
├── atlasvibe/          # Main package
│   ├── __init__.py
│   ├── cli.py          # CLI entry point
│   └── server.py       # Server entry point
├── captain/            # Backend application
├── blocks/             # Block libraries
├── electron_dist/      # Built Electron app (created during build)
├── main.py            # Legacy server entry point
└── setup.cfg          # Package configuration
```