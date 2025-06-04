TITLE: Publishing Python Package with uv (Console)
DESCRIPTION: This command uploads the built Python package to a configured package registry, such as PyPI. Authentication credentials can be provided via `--token`, `UV_PUBLISH_TOKEN`, or a username/password combination. For GitHub Actions, trusted publishers can be configured on PyPI to avoid explicit credential setup.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/guides/package.md#_snippet_2

LANGUAGE: console
CODE:
```
$ uv publish
```

----------------------------------------

TITLE: Managing Python Projects with uv
DESCRIPTION: This sequence of commands demonstrates the core project management workflow using `uv`. It covers initializing a new project, adding a dependency (`ruff`), running a command within the project's virtual environment, generating a lockfile, and synchronizing dependencies.
SOURCE: https://github.com/astral-sh/uv/blob/main/README.md#_snippet_5

LANGUAGE: bash
CODE:
```
$ uv init example
Initialized project `example` at `/home/user/example`

$ cd example

$ uv add ruff
Creating virtual environment at: .venv
Resolved 2 packages in 170ms
   Built example @ file:///home/user/example
Prepared 2 packages in 627ms
Installed 2 packages in 1ms
 + example==0.1.0 (from file:///home/user/example)
 + ruff==0.5.0

$ uv run ruff check
All checks passed!

$ uv lock
Resolved 2 packages in 0.33ms

$ uv sync
Resolved 2 packages in 0.70ms
Audited 1 package in 0.02ms
```

----------------------------------------

TITLE: Multi-stage Docker Build for uv Installation
DESCRIPTION: This Dockerfile demonstrates a multi-stage build process to install uv and manage Python dependencies. It uses an intermediate builder stage to install project dependencies and then copies only the virtual environment to the final slim image, optimizing image size and build time. It includes caching for uv and binding project files for dependency resolution.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/guides/integration/docker.md#_snippet_22

LANGUAGE: Dockerfile
CODE:
```
FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Change the working directory to the `app` directory
WORKDIR /app

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-editable

# Copy the project into the intermediate image
ADD . /app

# Sync the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable

FROM python:3.12-slim

# Copy the environment, but not the source code
COPY --from=builder --chown=app:app /app/.venv /app/.venv

# Run the application
CMD ["/app/.venv/bin/hello"]
```

----------------------------------------

TITLE: Creating Virtual Environment with Specific Python Version (uv)
DESCRIPTION: Demonstrates how to create a virtual environment using `uv` and explicitly specify a Python version (e.g., 3.11.6) for the environment. uv will automatically download and install the requested version if it's not already available on the system.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/concepts/python-versions.md#_snippet_0

LANGUAGE: Shell
CODE:
```
uv venv --python 3.11.6
```

----------------------------------------

TITLE: Activating Virtual Environment (macOS/Linux Console)
DESCRIPTION: Activates the virtual environment located at `.venv` in POSIX-compliant shells (like bash, zsh) on macOS and Linux. This makes the environment's Python and installed packages available in the current shell session.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/pip/environments.md#_snippet_4

LANGUAGE: console
CODE:
```
$ source .venv/bin/activate
```

----------------------------------------

TITLE: Creating Virtual Environment with Automatic Python Download via uv (Shell)
DESCRIPTION: This command creates a new virtual environment using `uv`. If no Python version is present on the system, `uv` will automatically download and install the latest Python version before proceeding with the virtual environment creation.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/guides/install-python.md#_snippet_7

LANGUAGE: Shell
CODE:
```
$ uv venv
```

----------------------------------------

TITLE: Installing uv via pip
DESCRIPTION: This command installs the `uv` package using `pip`, the standard Python package installer. This method requires a Python environment with `pip` already set up.
SOURCE: https://github.com/astral-sh/uv/blob/main/README.md#_snippet_2

LANGUAGE: bash
CODE:
```
pip install uv
```

----------------------------------------

TITLE: Adding a basic dependency with uv
DESCRIPTION: This command adds 'httpx' as a dependency to the project. An entry will be automatically added to the `project.dependencies` field in `pyproject.toml` with a compatible version constraint.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/concepts/projects/dependencies.md#_snippet_0

LANGUAGE: console
CODE:
```
$ uv add httpx
```

----------------------------------------

TITLE: Installing Python Dependencies with uv
DESCRIPTION: The `uv pip install` command installs packages into an environment. Like `uv pip sync`, it mutates the environment and triggers uv's environment discovery process.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/pip/environments.md#_snippet_16

LANGUAGE: Bash
CODE:
```
uv pip install
```

----------------------------------------

TITLE: Verifying uv Installation (Console)
DESCRIPTION: This snippet demonstrates how to verify that uv has been successfully installed and is accessible from the command line. Running the 'uv' command without arguments should display its help menu, confirming its presence and basic functionality.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/getting-started/first-steps.md#_snippet_0

LANGUAGE: Shell
CODE:
```
$ uv
An extremely fast Python package manager.

Usage: uv [OPTIONS] <COMMAND>

...
```

----------------------------------------

TITLE: Creating Default Virtual Environment with uv (Console)
DESCRIPTION: Creates a virtual environment in the default location (`.venv`) using the `uv` tool. This is the basic command for initializing a new environment.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/pip/environments.md#_snippet_0

LANGUAGE: console
CODE:
```
$ uv venv
```

----------------------------------------

TITLE: Installing Python Versions - uv CLI - Shell
DESCRIPTION: Installs a specific Python version using uv. This command simplifies the process of acquiring and setting up different Python interpreters for development environments.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/getting-started/features.md#_snippet_0

LANGUAGE: Shell
CODE:
```
uv python install
```

----------------------------------------

TITLE: Defining Base Requirements for Python Projects
DESCRIPTION: This snippet defines the base requirements for a Python project, specifying `starlette` and `fastapi` as direct dependencies. These are typically used as input for a dependency resolver like `uv pip compile` to generate a locked `requirements.txt` file.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/pip/compatibility.md#_snippet_1

LANGUAGE: Python
CODE:
```
starlette
fastapi
```

----------------------------------------

TITLE: Creating a Virtual Environment with uv
DESCRIPTION: The `uv venv` command is used to create a new virtual environment. uv will prompt the user to run this command if no virtual environment is found during discovery for mutation commands.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/pip/environments.md#_snippet_17

LANGUAGE: Bash
CODE:
```
uv venv
```

----------------------------------------

TITLE: Defining Project Dependencies in pyproject.toml
DESCRIPTION: This `pyproject.toml` file defines the project metadata, required Python version, and core dependencies (`fastapi`, `mangum`) for the application. It also includes a `dev` dependency group for development-specific packages like `fastapi[standard]`.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/guides/integration/aws-lambda.md#_snippet_1

LANGUAGE: toml
CODE:
```
[project]
name = "uv-aws-lambda-example"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
    # FastAPI is a modern web framework for building APIs with Python.
    "fastapi",
    # Mangum is a library that adapts ASGI applications to AWS Lambda and API Gateway.
    "mangum",
]

[dependency-groups]
dev = [
    # In development mode, include the FastAPI development server.
    "fastapi[standard]>=0.115",
]
```

----------------------------------------

TITLE: Declaring Project Dependencies in pyproject.toml
DESCRIPTION: This snippet demonstrates how to declare core project dependencies within the `pyproject.toml` file. Dependencies are listed under the `[project]` table in the `dependencies` array, specifying package names and optional version constraints.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/pip/dependencies.md#_snippet_0

LANGUAGE: toml
CODE:
```
[project]
dependencies = [
  "httpx",
  "ruff>=0.3.0"
]
```

----------------------------------------

TITLE: Declaring Python Version Requirement in pyproject.toml
DESCRIPTION: This TOML snippet demonstrates how to specify the required Python version for a project using the `requires-python` field within the `[project]` table of `pyproject.toml`. This setting ensures compatibility and influences dependency resolution for the project.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/concepts/projects/config.md#_snippet_0

LANGUAGE: toml
CODE:
```
[project]
name = "example"
version = "0.1.0"
requires-python = ">=3.12"
```

----------------------------------------

TITLE: Explicitly Syncing the Project Environment (Shell)
DESCRIPTION: This command explicitly syncs the project environment with the lockfile. It installs the necessary packages, making it particularly useful for ensuring development tools and editors have the correct dependencies.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/concepts/projects/sync.md#_snippet_5

LANGUAGE: Shell
CODE:
```
uv sync
```

----------------------------------------

TITLE: Combined Configuration for `flash-attn` with Metadata and Optional Dependencies (TOML)
DESCRIPTION: This comprehensive `pyproject.toml` configuration combines disabling build isolation for `flash-attn`, defining its build and compile dependencies as optional extras, and providing its metadata upfront. This setup streamlines the installation process for complex packages.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/concepts/projects/config.md#_snippet_17

LANGUAGE: toml
CODE:
```
[project]
name = "project"
version = "0.1.0"
description = "..."
readme = "README.md"
requires-python = ">=3.12"
dependencies = []

[project.optional-dependencies]
build = ["torch", "setuptools", "packaging"]
compile = ["flash-attn"]

[tool.uv]
no-build-isolation-package = ["flash-attn"]

[[tool.uv.dependency-metadata]]
name = "flash-attn"
version = "2.6.3"
requires-dist = ["torch", "einops"]
```

----------------------------------------

TITLE: Declaring a Basic Python Package Dependency
DESCRIPTION: This snippet shows a basic declaration for the 'numpy' package, commonly found in Python dependency files like `requirements.txt`. The trailing hash symbols are likely comments or extraneous characters.
SOURCE: https://github.com/astral-sh/uv/blob/main/crates/uv-requirements-txt/test-data/requirements-txt/whitespace.txt#_snippet_0

LANGUAGE: Python
CODE:
```
numpy  #  #
```

----------------------------------------

TITLE: Installing uv via pipx
DESCRIPTION: This command installs `uv` into an isolated environment using `pipx`, a tool for installing and running Python applications in isolated virtual environments. This ensures `uv` and its dependencies do not conflict with other Python projects.
SOURCE: https://github.com/astral-sh/uv/blob/main/README.md#_snippet_3

LANGUAGE: bash
CODE:
```
pipx install uv
```

----------------------------------------

TITLE: Installing Locked Requirements with uv pip
DESCRIPTION: This command uses `uv pip sync` to install all packages listed in a locked requirements file (`docs/requirements.txt`) into the current virtual environment. It efficiently resolves and installs the specified dependencies, ensuring reproducible installations.
SOURCE: https://github.com/astral-sh/uv/blob/main/README.md#_snippet_15

LANGUAGE: console
CODE:
```
$ uv pip sync docs/requirements.txt
Resolved 43 packages in 11ms
Installed 43 packages in 208ms
 + babel==2.15.0
 + black==24.4.2
 + certifi==2024.7.4
 ...
```

----------------------------------------

TITLE: Installing a Python Project and Dependencies with uv
DESCRIPTION: This Dockerfile snippet demonstrates a two-step process for installing a Python project and its dependencies. First, it copies pyproject.toml to install core dependencies, leveraging Docker's build cache. Then, it copies the entire project and installs it in editable mode, allowing for efficient caching of dependencies separate from frequently changing source code.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/guides/integration/docker.md#_snippet_29

LANGUAGE: Dockerfile
CODE:
```
COPY pyproject.toml .
RUN uv pip install -r pyproject.toml
COPY . .
RUN uv pip install -e .
```

----------------------------------------

TITLE: Installing multiple packages with uv pip
DESCRIPTION: Installs several Python packages simultaneously by listing them as arguments to the `uv pip install` command. This streamlines the process of setting up multiple dependencies at once.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/pip/packages.md#_snippet_2

LANGUAGE: console
CODE:
```
$ uv pip install flask ruff
```

----------------------------------------

TITLE: Managing uv Cache Manually with actions/cache (YAML)
DESCRIPTION: This comprehensive example shows how to manually manage the `uv` cache using GitHub's `actions/cache` action. It configures a constant cache location, restores the cache based on the runner's OS and `uv.lock` hash, and prunes the cache at the end of the job using `uv cache prune --ci` to optimize its size for CI environments.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/guides/integration/github.md#_snippet_12

LANGUAGE: yaml
CODE:
```
jobs:
  install_job:
    env:
      # Configure a constant location for the uv cache
      UV_CACHE_DIR: /tmp/.uv-cache

    steps:
      # ... setup up Python and uv ...

      - name: Restore uv cache
        uses: actions/cache@v4
        with:
          path: /tmp/.uv-cache
          key: uv-${{ runner.os }}-${{ hashFiles('uv.lock') }}
          restore-keys: |
            uv-${{ runner.os }}-${{ hashFiles('uv.lock') }}
            uv-${{ runner.os }}

      # ... install packages, run tests, etc ...

      - name: Minimize uv cache
        run: uv cache prune --ci
```

----------------------------------------

TITLE: Installing uv on Windows
DESCRIPTION: This PowerShell command downloads and executes the `uv` installation script on Windows. It uses `irm` (Invoke-RestMethod) to fetch the script and `iex` (Invoke-Expression) to run it, bypassing execution policy for the current session.
SOURCE: https://github.com/astral-sh/uv/blob/main/README.md#_snippet_1

LANGUAGE: powershell
CODE:
```
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

----------------------------------------

TITLE: Defining Python Package Dependencies
DESCRIPTION: This snippet defines specific versions for Python packages, ensuring consistent environments across different deployments. It's commonly used in `requirements.txt` files for dependency management.
SOURCE: https://github.com/astral-sh/uv/blob/main/crates/uv-requirements-txt/test-data/requirements-txt/small.txt#_snippet_0

LANGUAGE: Python
CODE:
```
tqdm==4.65.0
tomli-w==1.0.0
```

----------------------------------------

TITLE: Compile Requirements with uv pip
DESCRIPTION: Demonstrates compiling a requirements input file (`requirements.in`) into a locked, platform-independent requirements file (`requirements.txt`) using `uv pip compile`.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/index.md#_snippet_3

LANGUAGE: console
CODE:
```
$ uv pip compile docs/requirements.in \
   --universal \
   --output-file docs/requirements.txt
Resolved 43 packages in 12ms
```

----------------------------------------

TITLE: Installing a single package with uv pip
DESCRIPTION: Installs a specified Python package (e.g., Flask) into the active virtual environment using the `uv pip install` command. This is the basic method for adding new dependencies.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/pip/packages.md#_snippet_0

LANGUAGE: console
CODE:
```
$ uv pip install flask
```

----------------------------------------

TITLE: Optimizing Docker Builds with uv Intermediate Layers
DESCRIPTION: This multi-stage Dockerfile optimizes build times by separating dependency installation from project installation. It first installs `uv` and then uses `uv sync --locked --no-install-project` to install only project dependencies into a cached layer, copying the project contents later for a final sync.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/guides/integration/docker.md#_snippet_21

LANGUAGE: dockerfile
CODE:
```
# Install uv
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Change the working directory to the `app` directory
WORKDIR /app

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

# Copy the project into the image
ADD . /app

# Sync the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked
```

----------------------------------------

TITLE: Enabling Universal Resolution for uv pip (TOML)
DESCRIPTION: Activates universal resolution mode, aiming to generate a single `requirements.txt` file compatible across various operating systems, architectures, and Python implementations. The specified Python version acts as a lower bound for compatibility.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/reference/settings.md#_snippet_120

LANGUAGE: TOML
CODE:
```
[tool.uv.pip]
universal = true
```

LANGUAGE: TOML
CODE:
```
[pip]
universal = true
```

----------------------------------------

TITLE: Creating and Using Default Virtual Environment with uv (Console)
DESCRIPTION: Demonstrates creating a default virtual environment (`.venv`) and then installing a package (`ruff`) into it using `uv`. uv automatically detects the default environment for subsequent commands.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/pip/environments.md#_snippet_3

LANGUAGE: console
CODE:
```
$ uv venv
$ # Install a package in the new virtual environment
$ uv pip install ruff
```

----------------------------------------

TITLE: Changing a dependency's source to a local path
DESCRIPTION: This command updates the source for 'httpx' to a local path, allowing the project to use a local development version of the package instead of one from a registry or Git.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/concepts/projects/dependencies.md#_snippet_10

LANGUAGE: console
CODE:
```
$ uv add "httpx @ ../httpx"
```

----------------------------------------

TITLE: Creating New Virtual Environment - uv CLI - Shell
DESCRIPTION: Creates a new virtual environment, serving as a modern replacement for 'venv' and 'virtualenv'. This command isolates project dependencies.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/getting-started/features.md#_snippet_22

LANGUAGE: Shell
CODE:
```
uv venv
```

----------------------------------------

TITLE: Installing uv on macOS and Linux
DESCRIPTION: This command uses `curl` to download and execute the `uv` installation script on macOS and Linux systems. It's a standalone installer that does not require Rust or Python to be pre-installed.
SOURCE: https://github.com/astral-sh/uv/blob/main/README.md#_snippet_0

LANGUAGE: bash
CODE:
```
curl -LsSf https://astral.sh/uv/install.sh | sh
```

----------------------------------------

TITLE: Locking Dependencies from pyproject.toml using uv
DESCRIPTION: This command compiles dependencies defined in `pyproject.toml` and outputs the locked versions to `requirements.txt`. It ensures reproducibility by pinning exact dependency versions.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/pip/compile.md#_snippet_0

LANGUAGE: console
CODE:
```
$ uv pip compile pyproject.toml -o requirements.txt
```

----------------------------------------

TITLE: Locking Dependencies from requirements.in using uv
DESCRIPTION: This command compiles dependencies specified in `requirements.in` and writes the locked versions to `requirements.txt`. It's used when dependencies are declared in a `requirements.in` file.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/pip/compile.md#_snippet_1

LANGUAGE: console
CODE:
```
$ uv pip compile requirements.in -o requirements.txt
```

----------------------------------------

TITLE: Compiling Python Dependencies with uv
DESCRIPTION: This command uses the `uv` package manager to compile a `requirements.txt` style file (`flyte.in`) into a locked dependency list, ensuring reproducible builds. It resolves all transitive dependencies and pins them to specific versions.
SOURCE: https://github.com/astral-sh/uv/blob/main/scripts/requirements/compiled/flyte.txt#_snippet_0

LANGUAGE: Shell
CODE:
```
uv pip compile scripts/requirements/flyte.in
```

----------------------------------------

TITLE: Building Python Package with uv (Console)
DESCRIPTION: This command initiates the build process for a Python package using `uv`. By default, `uv build` processes the project in the current directory and places the generated distribution artifacts into a `dist/` subdirectory. It's a fundamental step before publishing a package.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/guides/package.md#_snippet_1

LANGUAGE: console
CODE:
```
$ uv build
```

----------------------------------------

TITLE: Defining a uv Workspace in pyproject.toml
DESCRIPTION: This TOML configuration defines a `uv` workspace in a `pyproject.toml` file. It specifies the project details, declares `bird-feeder` as a workspace-local dependency, and defines the workspace members using globs, excluding specific directories. This setup ensures `uv` manages multiple packages together with a consistent dependency set.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/concepts/projects/workspaces.md#_snippet_0

LANGUAGE: TOML
CODE:
```
[project]
name = "albatross"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["bird-feeder", "tqdm>=4,<5"]

[tool.uv.sources]
bird-feeder = { workspace = true }

[tool.uv.workspace]
members = ["packages/*"]
exclude = ["packages/seeds"]
```

----------------------------------------

TITLE: Creating Virtual Environment with Specific Python Version using uv (Console)
DESCRIPTION: Creates a virtual environment using a specific Python version (e.g., 3.11) with the `uv` tool. Requires the requested Python version to be available or downloadable by uv.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/pip/environments.md#_snippet_2

LANGUAGE: console
CODE:
```
$ uv venv --python 3.11
```

----------------------------------------

TITLE: Creating a Virtual Environment with uv
DESCRIPTION: This command creates a new virtual environment in the current directory using `uv venv`. It automatically detects the appropriate Python version and provides instructions for activating the environment.
SOURCE: https://github.com/astral-sh/uv/blob/main/README.md#_snippet_14

LANGUAGE: console
CODE:
```
$ uv venv
Using Python 3.12.3
Creating virtual environment at: .venv
Activate with: source .venv/bin/activate
```

----------------------------------------

TITLE: Defining Project Dependencies in pyproject.toml (TOML)
DESCRIPTION: This TOML snippet demonstrates how to define project dependencies within the `[project.dependencies]` table in `pyproject.toml`. It shows various dependency specifiers, including version ranges, exact versions, extras (e.g., `transformers[torch]`), and environment markers for conditional installation based on Python version.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/concepts/projects/dependencies.md#_snippet_14

LANGUAGE: toml
CODE:
```
[project]
name = "albatross"
version = "0.1.0"
dependencies = [
  # Any version in this range
  "tqdm >=4.66.2,<5",
  # Exactly this version of torch
  "torch ==2.2.2",
  # Install transformers with the torch extra
  "transformers[torch] >=4.39.3,<5",
  # Only install this package on older python versions
  # See "Environment Markers" for more information
  "importlib_metadata >=7.1.0,<8; python_version < '3.10'",
  "mollymawk ==0.1.0"
]
```

----------------------------------------

TITLE: Syncing Project Dependencies - uv CLI - Shell
DESCRIPTION: Synchronizes the project's dependencies with the environment based on the pyproject.toml or lockfile. This ensures that the installed packages match the project's declared requirements.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/getting-started/features.md#_snippet_11

LANGUAGE: Shell
CODE:
```
uv sync
```

----------------------------------------

TITLE: Project Dependency List (uv pip compile)
DESCRIPTION: This snippet shows the complete set of Python package dependencies, including their versions and the packages that require them. It was automatically generated by the 'uv pip compile' command to ensure reproducible builds for the project.
SOURCE: https://github.com/astral-sh/uv/blob/main/scripts/requirements/compiled/all-kinds.txt#_snippet_0

LANGUAGE: Python
CODE:
```
annotated-types==0.6.0
    # via pydantic
asgiref==3.7.2
    # via django
blinker==1.7.0
    # via flask
certifi==2023.11.17
    # via requests
cffi==1.16.0
    # via cryptography
charset-normalizer==3.3.2
    # via requests
click==8.1.7
    # via flask
cryptography==41.0.7
defusedxml==0.7.1
    # via python3-openid
django==5.0.1
    # via django-allauth
django-allauth==0.51.0
flask @ https://files.pythonhosted.org/packages/36/42/015c23096649b908c809c69388a805a571a3bea44362fe87e33fc3afa01f/flask-3.0.0-py3-none-any.whl
idna==3.6
    # via requests
itsdangerous==2.1.2
    # via flask
jinja2==3.1.2
    # via flask
markupsafe==2.1.3
    # via
    #   jinja2
    #   werkzeug
numpy==1.26.3
    # via pandas
oauthlib==3.2.2
    # via requests-oauthlib
pandas==2.1.4
pycparser==2.21
    # via cffi
pydantic==2.5.3
    # via pydantic-extra-types
pydantic-core==2.14.6
    # via pydantic
pydantic-extra-types @ git+https://github.com/pydantic/pydantic-extra-types.git@5ebc5bba58605c656a821eed773973725e35cf83
pyjwt==2.8.0
    # via django-allauth
python-dateutil==2.8.2
    # via pandas
python3-openid==3.2.0
    # via django-allauth
pytz==2023.3.post1
    # via pandas
requests==2.31.0
    # via
    #   django-allauth
    #   requests-oauthlib
requests-oauthlib==1.3.1
    # via django-allauth
six==1.16.0
    # via python-dateutil
sqlparse==0.4.4
    # via django
typing-extensions==4.9.0
    # via
    #   asgiref
    #   pydantic
    #   pydantic-core
tzdata==2023.4
    # via pandas
urllib3==2.1.0
    # via requests
werkzeug @ https://files.pythonhosted.org/packages/0d/cc/ff1904eb5eb4b455e442834dabf9427331ac0fa02853bf83db817a7dd53d/werkzeug-3.0.1.tar.gz
    # via flask
```

----------------------------------------

TITLE: Running Python Script with uv run (Console)
DESCRIPTION: Shows how to execute a Python script (`example.py`) within the project's environment using `uv run`. `uv run` handles environment activation and dependency resolution automatically.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/guides/projects.md#_snippet_2

LANGUAGE: console
CODE:
```
$ uv run example.py
```

----------------------------------------

TITLE: Compiling Platform-Specific Requirements with uv pip compile
DESCRIPTION: This command demonstrates how to use `uv pip compile` to generate a requirements file for a specific target platform and Python version. It allows users to compile dependencies for Python 3.10 on Linux, even when running on macOS with Python 3.12, ensuring platform-specific compatibility.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/concepts/resolution.md#_snippet_0

LANGUAGE: Shell
CODE:
```
uv pip compile --python-platform linux --python-version 3.10 requirements.in
```

----------------------------------------

TITLE: Installing an external project as an editable package with uv pip
DESCRIPTION: Installs a project located in a different directory as an editable package. This allows developers to work on a package's source code in one location and have changes instantly available in another project's virtual environment.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/pip/packages.md#_snippet_9

LANGUAGE: console
CODE:
```
$ uv pip install -e "ruff @ ./project/ruff"
```

----------------------------------------

TITLE: Declaring Python Package Dependencies with uv
DESCRIPTION: This snippet defines a comprehensive list of Python package dependencies and their exact versions, as generated by the `uv pip compile` command. It includes both primary dependencies like 'black' and their transitive dependencies, with comments indicating the origin of each package.
SOURCE: https://github.com/astral-sh/uv/blob/main/scripts/requirements/compiled/black.txt#_snippet_0

LANGUAGE: Python
CODE:
```
# This file was autogenerated by uv via the following command:
#    uv pip compile scripts/requirements/black.in
black==23.12.1
click==8.1.7
    # via black
mypy-extensions==1.0.0
    # via black
packaging==23.2
    # via black
pathspec==0.12.1
    # via black
platformdirs==4.1.0
    # via black
tomli==2.0.1
    # via black
typing-extensions==4.9.0
    # via black
```

----------------------------------------

TITLE: Installing packages from a pyproject.toml file with uv pip
DESCRIPTION: Installs packages defined within a `pyproject.toml` file. This command leverages the modern Python packaging standard to manage project dependencies, including build system requirements and project metadata.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/pip/packages.md#_snippet_11

LANGUAGE: console
CODE:
```
$ uv pip install -r pyproject.toml
```

----------------------------------------

TITLE: Executing Script with Declared Dependency (rich)
DESCRIPTION: This console command executes `example.py` using `uv run --with rich`. The `--with rich` option instructs `uv` to install the `rich` package before running the script, resolving the previous `ModuleNotFoundError`.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/guides/scripts.md#_snippet_12

LANGUAGE: console
CODE:
```
$ uv run --with rich example.py
For example: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:01
```

----------------------------------------

TITLE: Freezing Environment to requirements.txt (uv pip freeze)
DESCRIPTION: This command outputs all installed packages and their exact versions in a format compatible with `requirements.txt`. This is essential for reproducing the environment precisely.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/pip/inspection.md#_snippet_2

LANGUAGE: Shell
CODE:
```
$ uv pip freeze
```

----------------------------------------

TITLE: Configuring uv Docker Image in GitLab CI/CD
DESCRIPTION: This snippet defines a GitLab CI/CD job that uses a pre-built `uv` Docker image. It sets variables for `uv` and Python versions, base layer, and configures `UV_LINK_MODE` for build directory handling. The `image` field specifies the Docker image to use, and `script` is where `uv` commands would be executed.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/guides/integration/gitlab.md#_snippet_0

LANGUAGE: YAML
CODE:
```
variables:
  UV_VERSION: "0.5"
  PYTHON_VERSION: "3.12"
  BASE_LAYER: bookworm-slim
  # GitLab CI creates a separate mountpoint for the build directory,
  # so we need to copy instead of using hard links.
  UV_LINK_MODE: copy

uv:
  image: ghcr.io/astral-sh/uv:$UV_VERSION-python$PYTHON_VERSION-$BASE_LAYER
  script:
    # your `uv` commands
```

----------------------------------------

TITLE: Configuring Hash Requirement for uv pip (TOML)
DESCRIPTION: This setting enables hash-checking mode for `uv`'s `pip` functionality, requiring all package requirements to have corresponding hashes or be pinned to exact versions/direct URLs. It imposes constraints, disallowing Git, editable, and most local dependencies.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/reference/settings.md#_snippet_114

LANGUAGE: TOML
CODE:
```
[tool.uv.pip]
require-hashes = true
```

LANGUAGE: TOML
CODE:
```
[pip]
require-hashes = true
```

----------------------------------------

TITLE: Installing Python Version Satisfying Constraints (uv)
DESCRIPTION: Demonstrates installing a Python version that satisfies a specified version range (e.g., `>=3.8,<3.10`) using `uv python install`. uv will select and install a compatible version within the defined constraints.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/concepts/python-versions.md#_snippet_3

LANGUAGE: Shell
CODE:
```
uv python install '>=3.8,<3.10'
```

----------------------------------------

TITLE: Creating Project Lockfile - uv CLI - Shell
DESCRIPTION: Generates a lockfile for the project's dependencies, ensuring reproducible builds. This command captures the exact versions of all transitive dependencies.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/getting-started/features.md#_snippet_12

LANGUAGE: Shell
CODE:
```
uv lock
```

----------------------------------------

TITLE: Installing Specific Python Version with uv (Shell)
DESCRIPTION: This command installs a specific Python version, in this case, Python 3.12, using the `uv` tool. This allows users to target a precise runtime environment for their projects.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/guides/install-python.md#_snippet_1

LANGUAGE: Shell
CODE:
```
$ uv python install 3.12
```

----------------------------------------

TITLE: Compiling Requirements into Lockfile - uv CLI - Shell
DESCRIPTION: Compiles abstract requirements into a concrete lockfile, ensuring reproducible installations, similar to 'pip-tools compile'. This command resolves and pins all transitive dependencies.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/getting-started/features.md#_snippet_30

LANGUAGE: Shell
CODE:
```
uv pip compile
```

----------------------------------------

TITLE: Running FastAPI Application Locally with uv
DESCRIPTION: This command demonstrates how to execute the FastAPI development server locally using `uv`. The `uv run` command acts as a wrapper, allowing `uv` to manage the environment and dependencies before running the specified command (`fastapi dev`).
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/guides/integration/aws-lambda.md#_snippet_3

LANGUAGE: console
CODE:
```
$ uv run fastapi dev
```

----------------------------------------

TITLE: Pinning uv Version by SHA256 Checksum
DESCRIPTION: This Dockerfile snippet shows an even more robust method for reproducible builds: pinning the `uv` image by its SHA256 checksum. This guarantees that the exact same image content is used, regardless of tag changes, making builds highly consistent and secure.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/guides/integration/docker.md#_snippet_4

LANGUAGE: dockerfile
CODE:
```
COPY --from=ghcr.io/astral-sh/uv@sha256:2381d6aa60c326b71fd40023f921a0a3b8f91b14d5db6b90402e65a635053709 /uv /uvx /bin/
```

----------------------------------------

TITLE: Installing Specific Python Patch Version (uv)
DESCRIPTION: Illustrates how to install a precise patch version of Python (e.g., 3.12.3) using the `uv python install` command. This ensures a specific, stable release is available for use.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/concepts/python-versions.md#_snippet_1

LANGUAGE: Shell
CODE:
```
uv python install 3.12.3
```

----------------------------------------

TITLE: Compiling requirements files with pre-commit (YAML)
DESCRIPTION: Defines a pre-commit hook to compile `requirements.in` into `requirements.txt` using the `pip-compile` hook. The `args` parameter specifies the input and output files for the compilation process, ensuring dependencies are compiled automatically.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/guides/integration/pre-commit.md#_snippet_2

LANGUAGE: yaml
CODE:
```
repos:
  - repo: https://github.com/astral-sh/uv-pre-commit
    # uv version.
    rev: 0.7.9
    hooks:
      # Compile requirements
      - id: pip-compile
        args: [requirements.in, -o, requirements.txt]
```

----------------------------------------

TITLE: Defining Python Package Requirements with Version Constraints
DESCRIPTION: This `requirements.txt` snippet specifies dependencies for a Python project, including `dill` with a version range and `apache-beam` up to a specific maximum version. It's used to define the packages and their acceptable versions for `uv` to resolve.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/reference/troubleshooting/build-failures.md#_snippet_9

LANGUAGE: Python
CODE:
```
dill<0.3.9,>=0.2.2
apache-beam<=2.49.0
```

----------------------------------------

TITLE: Defining a Version Constraint in constraints.txt
DESCRIPTION: This snippet shows how to define a version constraint for a package, `pydantic`, in a `constraints.txt` file. It specifies that `pydantic` must be less than version 2.0, without triggering its installation.
SOURCE: https://github.com/astral-sh/uv/blob/main/docs/pip/compile.md#_snippet_14

LANGUAGE: python
CODE:
```
pydantic<2.0
```