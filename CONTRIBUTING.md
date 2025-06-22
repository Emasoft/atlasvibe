# Contributing to AtlasVibe

First off, thank you for considering contributing to AtlasVibe! It's people like you that make AtlasVibe such a great tool.

## ⚠️ Important Note

AtlasVibe is currently in **early alpha stage**. This means:

- The codebase is rapidly evolving
- APIs may change without notice
- Documentation may be outdated
- Some features are incomplete

We appreciate your patience and understanding as we work towards a stable release.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Process](#development-process)
- [Style Guidelines](#style-guidelines)
- [Commit Messages](#commit-messages)
- [Pull Request Process](#pull-request-process)
- [Community](#community)

## Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

### Our Standards

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on what is best for the community
- Show empathy towards other community members

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/atlasvibe.git
   cd atlasvibe
   ```
3. **Set up the development environment**:
   ```bash
   ./setup-git-env.sh
   uv sync --all-extras --dev
   pre-commit install
   ```
4. **Create a branch** for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## How Can I Contribute?

### 🐛 Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates.

**When reporting bugs, include:**

- A clear and descriptive title
- Steps to reproduce the issue
- Expected behavior vs actual behavior
- Screenshots (if applicable)
- System information (OS, Python version, Node version)
- Relevant log output

### 💡 Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues.

**When suggesting enhancements, include:**

- A clear and descriptive title
- Detailed description of the proposed feature
- Rationale for why this would be useful
- Possible implementation approach (optional)
- Mockups or examples (if applicable)

### 📝 Improving Documentation

Documentation improvements are always welcome! This includes:

- Fixing typos or unclear explanations
- Adding examples
- Improving API documentation
- Creating tutorials or guides

### 🔧 Contributing Code

#### Your First Code Contribution

Unsure where to begin? Look for issues labeled:

- `good first issue` - Simple issues for newcomers
- `help wanted` - Issues where we need community help
- `documentation` - Documentation improvements

#### Development Workflow

1. **Make your changes** following our style guidelines
2. **Add or update tests** for your changes
3. **Run tests locally**:
   ```bash
   uv run pytest
   pnpm test
   ```
4. **Run linters**:
   ```bash
   pre-commit run --all-files
   ```
5. **Commit your changes** with a descriptive commit message

## Development Process

### 🏗️ Architecture Overview

Before contributing, familiarize yourself with:

- **Frontend**: React + TypeScript + Electron
- **Backend**: Python + FastAPI + Prefect
- **Block System**: Modular Python functions with metadata

### 🧪 Testing Requirements

All code contributions must include appropriate tests:

- **Python**: Use pytest, aim for >80% coverage
- **TypeScript**: Use Jest/Vitest, aim for >70% coverage
- **E2E**: Add Playwright tests for critical user paths

Run all tests with:

```bash
./runtests.sh
```

### 🔍 Code Review Process

All submissions require review:

1. Automated checks must pass (linting, tests, security)
2. At least one maintainer approval required
3. All review comments must be addressed
4. Branch must be up-to-date with main

## Style Guidelines

### Python Style Guide

We use [Ruff](https://github.com/astral-sh/ruff) for Python formatting and linting:

```python
# Good example
def calculate_sum(numbers: List[float]) -> float:
    """Calculate the sum of a list of numbers.

    Args:
        numbers: List of numbers to sum

    Returns:
        The sum of all numbers
    """
    return sum(numbers)
```

**Key points:**

- Use type hints for all functions
- Write docstrings for all public functions
- Follow PEP 8 with Ruff's modern interpretations
- Maximum line length: 88 characters

### TypeScript/JavaScript Style Guide

We use ESLint and Prettier for TypeScript/JavaScript:

```typescript
// Good example
export const calculateSum = (numbers: number[]): number => {
  return numbers.reduce((acc, curr) => acc + curr, 0);
};
```

**Key points:**

- Use TypeScript for all new code
- Prefer functional components for React
- Use meaningful variable names
- Document complex logic with comments

### Block Development Guidelines

When creating new blocks:

```python
@atlasvibe(
    display_name="My Block",
    category="CATEGORY/SUBCATEGORY",
    inputs={"data": pd.DataFrame},
    outputs={"result": pd.DataFrame},
)
def my_block(data: pd.DataFrame) -> pd.DataFrame:
    """Process data and return results.

    This block performs specific data processing...

    Parameters
    ----------
    data : pd.DataFrame
        Input data to process

    Returns
    -------
    pd.DataFrame
        Processed data
    """
    # Implementation here
    return processed_data
```

## Commit Messages

We follow [Conventional Commits](https://www.conventionalcommits.org/):

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Test additions or modifications
- `chore`: Maintenance tasks
- `perf`: Performance improvements

### Examples

```bash
# Good
feat(blocks): add CSV export block
fix(ui): resolve connection line rendering issue
docs(readme): update installation instructions

# Bad
Fixed stuff
Update code
Added new feature
```

## Pull Request Process

### Before Submitting

1. **Update documentation** for any API changes
2. **Add tests** for new functionality
3. **Run all checks locally**:
   ```bash
   pre-commit run --all-files
   uv run pytest
   pnpm test
   ```
4. **Update CHANGELOG.md** (if applicable)

### PR Template

When creating a PR, include:

```markdown
## Description

Brief description of changes

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing

- [ ] Tests pass locally
- [ ] Added new tests
- [ ] Updated existing tests

## Checklist

- [ ] My code follows the style guidelines
- [ ] I have performed a self-review
- [ ] I have commented my code where necessary
- [ ] I have updated the documentation
- [ ] My changes generate no new warnings
```

### Review Process

1. **Automated checks** run immediately
2. **Maintainer review** within 48-72 hours
3. **Address feedback** promptly
4. **Merge** once approved and checks pass

## Community

### Getting Help

- **Discord**: [Join our server](https://discord.gg/atlasvibe) (coming soon)
- **Discussions**: Use GitHub Discussions for questions
- **Issues**: For bug reports and feature requests

### Recognition

Contributors are recognized in:

- The README.md file
- Release notes
- Our contributors page

### Becoming a Maintainer

Active contributors may be invited to become maintainers. Maintainers:

- Have write access to the repository
- Help review and merge PRs
- Participate in project planning
- Guide the project direction

## Thank You!

Your contributions make AtlasVibe better for everyone. We appreciate your time and effort in helping improve this project!

---

**Questions?** Feel free to ask in [GitHub Discussions](https://github.com/Emasoft/atlasvibe/discussions) or reach out to the maintainers.
