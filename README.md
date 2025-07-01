<div align="center">

# AtlasVibe

### Visual Programming IDE for Python

[![CI Status](https://github.com/Emasoft/atlasvibe/actions/workflows/ci.yml/badge.svg)](https://github.com/Emasoft/atlasvibe/actions/workflows/ci.yml)
[![CD Status](https://github.com/Emasoft/atlasvibe/actions/workflows/cd.yaml/badge.svg)](https://github.com/Emasoft/atlasvibe/actions/workflows/cd.yaml)
[![Pre-commit](https://github.com/Emasoft/atlasvibe/actions/workflows/pre-commit.yml/badge.svg)](https://github.com/Emasoft/atlasvibe/actions/workflows/pre-commit.yml)
[![Dependency Check](https://github.com/Emasoft/atlasvibe/actions/workflows/dependency-check.yml/badge.svg)](https://github.com/Emasoft/atlasvibe/actions/workflows/dependency-check.yml)

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Node 20+](https://img.shields.io/badge/node-20+-green.svg)](https://nodejs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Managed with uv](https://img.shields.io/badge/managed%20with-uv-blue)](https://github.com/astral-sh/uv)

[**Documentation**](#documentation) • [**Installation**](#installation) • [**Quick Start**](#quick-start) • [**Contributing**](#contributing)

</div>

---

<div align="center">

## ⚠️ EARLY ALPHA WARNING ⚠️

**This project is in early alpha stage and is NOT ready for production use.**

**USE AT YOUR OWN RISK**

- 🚧 APIs and features are subject to breaking changes
- 🐛 Expect bugs and incomplete features
- 📚 Documentation may be incomplete or outdated
- 💾 Data formats may change without migration paths

**We strongly recommend waiting for a stable release before using in any production environment.**

</div>

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Project Status](#project-status)
- [System Requirements](#system-requirements)
- [Installation](#installation)
  - [Quick Install](#quick-install)
  - [Manual Installation](#manual-installation)
  - [Developer Setup](#developer-setup)
- [Quick Start](#quick-start)
- [Documentation](#documentation)
  - [CLI Reference](#cli-reference)
  - [API Documentation](#api-documentation)
- [Development](#development)
  - [Architecture](#architecture)
  - [Building from Source](#building-from-source)
  - [Testing](#testing)
  - [CI/CD Pipeline](#cicd-pipeline)
- [Contributing](#contributing)
- [Security](#security)
- [License](#license)
- [Acknowledgments](#acknowledgments)
- [Support](#support)

## 🎯 Overview

AtlasVibe is an open-source visual programming IDE for Python that enables users to create complex applications through an intuitive node-based interface. Built with modern web technologies and designed for extensibility, AtlasVibe aims to make Python programming more accessible while maintaining the full power of the language.

### 🌟 Vision

Our goal is to create a visual development environment where:

- 🔗 Complex Python workflows can be built by connecting visual nodes
- 🤖 AI capabilities enhance node creation and modification
- 🎨 The interface is intuitive for beginners yet powerful for experts
- 🔧 Every aspect is extensible and customizable

## ✨ Features

### Current Features (Alpha)

- ✅ **Visual Node Editor** - Drag-and-drop interface with ReactFlow
- ✅ **Python Block System** - Modular Python execution units
- ✅ **Real-time Execution** - See results as you build
- ✅ **Project Management** - Organize workflows and custom blocks
- ✅ **Cross-platform** - Works on Windows, macOS, and Linux

### Planned Features

- 🔄 **AI-Powered Nodes** - Self-modifying blocks based on intent
- 📦 **Block Marketplace** - Share and discover community blocks
- 🔌 **Plugin System** - Extend functionality with plugins
- 📊 **Advanced Visualizations** - Built-in data visualization tools
- 🌐 **Cloud Collaboration** - Real-time collaborative editing

## 📊 Project Status

<div align="center">

| Component     | Status         | Progress                            |
| ------------- | -------------- | ----------------------------------- |
| Core Engine   | 🟡 Alpha       | ![70%](https://progress-bar.dev/70) |
| Block System  | 🟡 Alpha       | ![65%](https://progress-bar.dev/65) |
| UI/UX         | 🟡 Alpha       | ![60%](https://progress-bar.dev/60) |
| Documentation | 🟠 In Progress | ![40%](https://progress-bar.dev/40) |
| Testing       | 🟠 In Progress | ![50%](https://progress-bar.dev/50) |
| CI/CD         | 🟢 Operational | ![90%](https://progress-bar.dev/90) |

</div>

### Current Focus

1. 🔨 Refactoring core architecture from Flojoy Studio base
2. 🎯 Implementing project-centric block management
3. 🧪 Expanding test coverage
4. 📝 Improving documentation

## 💻 System Requirements

### Minimum Requirements

- **OS**: Windows 10+, macOS 10.15+, Ubuntu 20.04+
- **Python**: 3.11 or higher
- **Node.js**: 20.x or higher
- **RAM**: 4GB
- **Storage**: 2GB free space

### Recommended Requirements

- **RAM**: 8GB or more
- **Storage**: 5GB free space
- **Display**: 1920x1080 or higher

### Development Requirements

- **Git**: 2.x or higher
- **GitHub CLI**: For automated setup (optional)
- **Docker**: For containerized development (optional)

## 📦 Installation

### Quick Install

#### Using the Installation Script (Recommended)

```bash
# Clone the repository
git clone https://github.com/Emasoft/atlasvibe.git
cd atlasvibe

# Run the automated installer
./install.sh

# After installation, run AtlasVibe
atlasvibe run
```

The installation script will:

- ✅ Check system requirements
- ✅ Install uv package manager
- ✅ Set up Python environment
- ✅ Install all dependencies
- ✅ Build the application
- ✅ Create command-line shortcuts

### Manual Installation

<details>
<summary>Click to expand manual installation steps</summary>

#### 1. Install Prerequisites

```bash
# Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install pnpm (Node package manager)
npm install -g pnpm
```

#### 2. Clone and Setup

```bash
# Clone repository
git clone https://github.com/Emasoft/atlasvibe.git
cd atlasvibe

# Create Python environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install Python dependencies
uv sync --all-extras
```

#### 3. Build Application

```bash
# Install Node dependencies
pnpm install

# Build frontend
pnpm run build

# Build Electron app
pnpm run electron-package:mac   # macOS
pnpm run electron-package:win   # Windows
pnpm run electron-package:linux # Linux

# Install AtlasVibe package
uv pip install -e .
```

</details>

### Developer Setup

<details>
<summary>Click to expand developer setup</summary>

```bash
# Clone with full history
git clone --recursive https://github.com/Emasoft/atlasvibe.git
cd atlasvibe

# Set up development environment
./setup-git-env.sh          # Configure git
./setup-github-cicd.sh      # Set up CI/CD (requires gh CLI)

# Install with dev dependencies
uv sync --all-extras --dev

# Install pre-commit hooks
uv pip install pre-commit
pre-commit install --install-hooks

# Verify setup
pre-commit run --all-files  # Should pass all checks
uv run pytest              # Should pass all tests
```

</details>

## 🚀 Quick Start

### 1. Create Your First Project

```bash
# Create a new project
atlasvibe init my-first-project
cd my-first-project

# Start AtlasVibe
atlasvibe run
```

### 2. Build Your First Workflow

1. **Add Blocks**: Drag blocks from the palette to the canvas
2. **Connect Nodes**: Draw connections between block ports
3. **Configure**: Click blocks to set parameters
4. **Execute**: Press the Run button to execute your workflow

### 3. Example: Simple Data Processing

```python
# Example workflow:
# [CSV Reader] → [Data Filter] → [Plot Generator] → [File Writer]
```

<details>
<summary>See example code</summary>

```python
# Each block is a Python function with the @atlasvibe decorator
@atlasvibe(
    display_name="CSV Reader",
    category="DATA/IO",
    inputs={"file_path": str},
    outputs={"data": pd.DataFrame}
)
def read_csv(file_path: str) -> pd.DataFrame:
    """Read CSV file and return DataFrame."""
    return pd.read_csv(file_path)
```

</details>

## 📚 Documentation

### CLI Reference

AtlasVibe provides a comprehensive command-line interface:

```bash
atlasvibe --help  # Show all available commands
```

#### Core Commands

| Command  | Description                      | Options                 |
| -------- | -------------------------------- | ----------------------- |
| `run`    | Start full application (default) | -                       |
| `server` | Run backend server only          | `--port`, `--log-level` |
| `ui`     | Run frontend UI only             | `--dev`                 |
| `init`   | Create new project               | `PATH` (required)       |

#### Examples

```bash
# Start AtlasVibe (full application)
atlasvibe run

# Run server on custom port with debug logging
atlasvibe server --port 8080 --log-level DEBUG

# Run UI in development mode (hot reload)
atlasvibe ui --dev

# Initialize project with custom name
atlasvibe init ~/projects/my-workflow
```

### API Documentation

When running the server, API documentation is available at:

- **Swagger UI**: http://localhost:5392/docs
- **ReDoc**: http://localhost:5392/redoc

## 🛠️ Development

### Architecture

```
atlasvibe/
├── src/                    # Frontend source (React/TypeScript)
│   ├── main/              # Electron main process
│   └── renderer/          # React application
├── captain/               # Backend source (Python/FastAPI)
│   ├── routes/           # API endpoints
│   ├── services/         # Business logic
│   └── models/           # Data models
├── blocks/               # Block library
│   └── [CATEGORY]/       # Categorized blocks
├── pkgs/                 # Internal packages
│   ├── atlasvibe/       # Core SDK
│   └── atlasvibe_sdk/   # Block SDK
└── tests/               # Test suites
```

### Building from Source

```bash
# Full build
pnpm run build

# Watch mode (development)
pnpm run dev

# Build specific platforms
pnpm run electron-package:mac
pnpm run electron-package:win
pnpm run electron-package:linux
```

### Testing

#### Running Tests

```bash
# Run all tests
./runtests.sh

# Python tests only
uv run pytest
uv run pytest --cov  # With coverage

# Frontend tests
pnpm test

# E2E tests
pnpm run e2e

# Run ALL tests (including slow tests)
./run_all_tests.sh
```

#### Test Coverage

We aim for high test coverage:

- Python backend: >80%
- Frontend components: >70%
- E2E scenarios: Critical paths

### CI/CD Pipeline

Our CI/CD pipeline ensures code quality and reliability:

#### Workflows

| Workflow         | Trigger          | Purpose             |
| ---------------- | ---------------- | ------------------- |
| **CI**           | Push/PR          | Code quality, tests |
| **CD**           | Tags `v*`        | Build releases      |
| **Security**     | Push/PR/Schedule | Secret scanning     |
| **Dependencies** | Weekly           | Dependency analysis |
| **Pre-commit**   | PR               | Code formatting     |

#### Local CI Simulation

```bash
# Run all CI checks locally
pre-commit run --all-files

# Run specific checks
uv run ruff check .
uv run mypy .
pnpm run lint
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Quick Contribution Guide

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'feat: add amazing feature'`)
4. **Push** to your fork (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### Commit Convention

We use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `test:` Test additions/modifications
- `refactor:` Code refactoring
- `chore:` Maintenance tasks

## 🔒 Security

### Reporting Security Issues

**⚠️ Do not report security vulnerabilities through public issues.**

Please report security vulnerabilities to our security team by following the instructions in [SECURITY.md](SECURITY.md).

### Security Measures

- 🔍 Automated secret scanning with Gitleaks
- 📦 Regular dependency updates via Dependabot
- 🛡️ Security-focused code reviews
- 🔐 Signed releases (coming soon)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2024 Emasoft
Copyright (c) 2023-2024 Flojoy (for the original Flojoy Studio software)
```

For third-party licenses and dependencies, see [THIRD-PARTY-LICENSES.md](THIRD-PARTY-LICENSES.md).

## 🙏 Acknowledgments

AtlasVibe is built upon the foundation of [**Flojoy Studio**](https://github.com/flojoy-ai/studio), an open-source test sequencer for hardware validation. We are deeply grateful to the Flojoy team for their excellent work and for making it available under the MIT license.

Special thanks to:

- The Flojoy Studio team for the original codebase
- All contributors who have helped shape this project
- The open-source community for invaluable tools and libraries

## 💬 Support

### Community

- **GitHub Issues**: [Bug reports and feature requests](https://github.com/Emasoft/atlasvibe/issues)
- **GitHub Discussions**: [Community discussions](https://github.com/Emasoft/atlasvibe/discussions)
- **Wiki**: [Documentation and guides](https://github.com/Emasoft/atlasvibe/wiki) (coming soon)

### Getting Help

1. 📖 Check the [documentation](#documentation)
2. 🔍 Search [existing issues](https://github.com/Emasoft/atlasvibe/issues)
3. 💬 Ask in [discussions](https://github.com/Emasoft/atlasvibe/discussions)
4. 🐛 Report bugs via [issues](https://github.com/Emasoft/atlasvibe/issues/new)

---

<div align="center">

**Built with ❤️ by [Emasoft](https://github.com/Emasoft) and contributors**

[⬆ Back to top](#atlasvibe)

</div>
