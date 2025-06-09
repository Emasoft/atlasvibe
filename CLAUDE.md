# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## General Development Guidelines and Rules
- *CRITICAL*: when reading the lines of the source files, do not read just few lines like you usually do. Instead always read all the lines of the file (until you reach the limit of available context memory). No matter what is the situation, searching or editing a file, ALWAYS OBEY TO THIS RULE!!!.
- be extremely meticulous and accurate. always check twice any line of code for errors before output the code.
- never output code that is abridged or with parts replaced by placeholder comments like `# ... rest of the code ...`, `# ... rest of the function as before ...`, `# ... rest of the code remains the same ...`, or similar. You are not chatting. The code you output is going to be saved and linted, so omitting parts of it will cause errors and broken files.
- Be conservative. only change the code that it is strictly necessary to change to implement a feature or fix an issue. Do not change anything else. You must report the user if there is a way to improve certain parts of the code, but do not attempt to do it unless the user explicitly asks you to. 
- when fixing the code, if you find that there are multiple possible solutions, do not start immediately but first present the user all the options and ask him to choose the one to try. For trivial bugs you don't need to, of course.
- never remove unused code or variables unless they are wrong, since the program is a WIP and those unused parts are likely going to be developed and used in the future. The only exception is if the user explicitly tells you to do it.
- Don't worry about functions imported from external modules, since those dependencies cannot be always included in the chat for your context limit. Do not remove them or implement them just because you can''t find the module or source file they are imported from. You just assume that the imported modules and imported functions work as expected. If you need to change them, ask the user to include them in the chat.
- spend a long time thinking deeply to understand completely the code flow and inner working of the program before writing any code or making any change. 
- if the user asks you to implement a feature or to make a change, always check the source code to ensure that the feature was not already implemented before or it is implemented in another form. Never start a task without checking if that task was already implemented or done somewhere in the codebase.
- if you must write a function, always check if there are already similar functions that can be extended or parametrized to do what new function need to do. Avoid writing duplicated or similar code by reusing the same flexible helper functions where is possible.
- keep the source files as small as possible. If you need to create new functions or classes, prefer creating them in new modules in new files and import them instead of putting them in the same source file that will use them. Small reusable modules are always preferable to big functions and spaghetti code.
- try to edit only one source file at time. Keeping only one file at time in the context memory will be optimal. When you need to edit another file, ask the user to remove from the chat context the previous one and to add the new one. You can aleays use the repo map to get an idea of the content of the other files.
- always use type annotations
- always keep the size of source code files below 10Kb. If writing new code in a source file will make the file size bigger than 10Kb, create a new source file , write the code there, nd import it as a module. Refactor big files in multiple smaller modules.
- always preserve comments and add them when writing new code.
- always write the docstrings of all functions and improve the existing ones. 
- only use google style docstrings, but do not use markdown. 
- never use markdown in comments.
- when using the Bash tool, always set the timeout parameter to 1200000 (20 minutes).
- always tabulate the tests result in a nice table.
- do not use mockup tests or mocked behaviours unless it is absolutely impossible to do otherwise. If you need to use a service, local or remote, do not mock it, just ask the user to activate it for the duration of the tests. Results of mocked tests are completely useless. Only real tests can discover issues with the codebase.
- always use a **Test-Driven Development (TDD)** methodology (write tests first, the implementation later) when implementing new features or change the existing ones. But first check that the existing tests are written correctly.
- always plan in advance your actions, and break down your plan into very small tasks. Save a file named `DEVELOPMENT_PLAN.md` and write all tasks inside it. Update it with the status of each tasks after any changes.
- do not create prototypes or sketched, abridged versions of the features you need to develop. That is only a waste of time. Instead break down the new features in its elemental components and functions, subdivide it in small autonomous modules with a specific function, and develop one module at time. When each module will be completed (passing the test for the module), then you will be able to implement the original feature easily just combining the modules. The modules can be helper functions, data structures, external librries, anything that is focused and reusable. Prefer functions at classes, but you can create small classes as specialized handlers for certain data and tasks, then also classes can be used as pieces for building the final feature.
- Commit often. Never mention Claude as the author of the commits.
- **Auto-Lint after changes**: Always run a linter (like ruff or shellcheck) after any changes to the files.
- always add the following shebang at the beginning of each python file: 

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
```
- always add a short changelog before the imports in of the source code to document all the changes you made to it.

```python
# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# <your changelog here…>
# 
```

## Examples Of Development Commands

### Environment Setup
```bash
# Python environment (using uv)
uv venv
source .venv/bin/activate  # Linux/macOS
.venv_windows\Scripts\activate     # Windows
uv sync --all-extras       # Install all dependencies

# Node.js dependencies
pnpm install
```

### Running the Application
```bash
# Full stack (frontend + backend)
pnpm run start-project            # macOS/Linux
pnpm run start-project:win        # Windows
pnpm run start-project:debug      # Debug mode

# Backend only
uv run python3 main.py            # or: python main.py on Windows
uv run python3 main.py --log-level debug  # Debug mode

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

------------------------------------------

## Managed and system Python installations
Since it is common for a system to have an existing Python installation, uv supports discovering Python versions. However, uv also supports installing Python versions itself. To distinguish between these two types of Python installations, uv refers to Python versions it installs as managed Python installations and all other Python installations as system Python installations.

Note
uv does not distinguish between Python versions installed by the operating system vs those installed and managed by other tools. For example, if a Python installation is managed with pyenv, it would still be considered a system Python version in uv.


## Requesting a version
A specific Python version can be requested with the --python flag in most uv commands. For example, when creating a virtual environment:


$ uv venv --python 3.11.6

uv will ensure that Python 3.11.6 is available — downloading and installing it if necessary — then create the virtual environment with it.
The following Python version request formats are supported:

	•	<version> (e.g., 3, 3.12, 3.12.3)
	•	<version-specifier> (e.g., >=3.12,<3.13)
	•	<implementation> (e.g., cpython or cp)
	•	<implementation>@<version> (e.g., cpython@3.12)
	•	<implementation><version> (e.g., cpython3.12 or cp312)
	•	<implementation><version-specifier> (e.g., cpython>=3.12,<3.13)
	•	<implementation>-<version>-<os>-<arch>-<libc> (e.g., cpython-3.12.3-macos-aarch64-none)
	
Additionally, a specific system Python interpreter can be requested with:

	•	<executable-path> (e.g., /opt/homebrew/bin/python3)
	•	<executable-name> (e.g., mypython3)
	•	<install-dir> (e.g., /some/environment/)
	
By default, uv will automatically download Python versions if they cannot be found on the system. This behavior can be disabled with the python-downloads option.


## Python version files
The .python-version file can be used to create a default Python version request. uv searches for a .python-version file in the working directory and each of its parents. If none is found, uv will check the user-level configuration directory. Any of the request formats described above can be used, though use of a version number is recommended for interoperability with other tools.
A .python-version file can be created in the current directory with the uv python pin command:

## Change to use a specific Python version in the current directory

```
$ uv python pin 3.11

Pinned `.python-version` to `3.11`
```

A global .python-version file can be created in the user configuration directory with the uv python pin --global command. (not reccomended)

## Discovery of .python-version files can be disabled with --no-config.
uv will not search for .python-version files beyond project or workspace boundaries (with the exception of the user configuration directory).

## Installing a Python version
uv bundles a list of downloadable CPython and PyPy distributions for macOS, Linux, and Windows.

Tip
By default, Python versions are automatically downloaded as needed without using uv python install.

To install a Python version at a specific version:


$ uv python install 3.12.3

To install the latest patch version:


$ uv python install 3.12

To install a version that satisfies constraints:


$ uv python install '>=3.8,<3.10'

To install multiple versions:


$ uv python install 3.9 3.10 3.11

To install a specific implementation:


$ uv python install pypy

All of the Python version request formats are supported except those that are used for requesting local interpreters such as a file path.
By default uv python install will verify that a managed Python version is installed or install the latest version. If a .python-version file is present, uv will install the Python version listed in the file. A project that requires multiple Python versions may define a .python-versions file. If present, uv will install all of the Python versions listed in the file.

Important
The available Python versions are frozen for each uv release. To install new Python versions, you may need upgrade uv.

## Installing Python executables

To install Python executables into your PATH, provide the --preview option:


$ uv python install 3.12 --preview
This will install a Python executable for the requested version into ~/.local/bin, e.g., as python3.12.

Tip
If ~/.local/bin is not in your PATH, you can add it with uv tool update-shell.

To install python and python3 executables, include the --default option:


$ uv python install 3.12 --default --preview

When installing Python executables, uv will only overwrite an existing executable if it is managed by uv — e.g., if ~/.local/bin/python3.12 exists already uv will not overwrite it without the --force flag.
uv will update executables that it manages. However, it will prefer the latest patch version of each Python minor version by default. For example:


$ uv python install 3.12.7 --preview  # Adds `python3.12` to `~/.local/bin`

$ uv python install 3.12.6 --preview  # Does not update `python3.12`

$ uv python install 3.12.8 --preview  # Updates `python3.12` to point to 3.12.8

## Project Python versions
uv will respect Python requirements defined in requires-python in the pyproject.toml file during project command invocations. The first Python version that is compatible with the requirement will be used, unless a version is otherwise requested, e.g., via a .python-version file or the --python flag.

## Viewing available Python versions
To list installed and available Python versions:

$ uv python list

To filter the Python versions, provide a request, e.g., to show all Python 3.13 interpreters:


$ uv python list 3.13

Or, to show all PyPy interpreters:

$ uv python list pypy

By default, downloads for other platforms and old patch versions are hidden.
To view all versions:

$ uv python list --all-versions

To view Python versions for other platforms:


$ uv python list --all-platforms

To exclude downloads and only show installed Python versions:


$ uv python list --only-installed

See the uv python list reference for more details.

## Finding a Python executable
To find a Python executable, use the uv python find command:

$ uv python find

By default, this will display the path to the first available Python executable. See the discovery rules for details about how executables are discovered.

This interface also supports many request formats, e.g., to find a Python executable that has a version of 3.11 or newer:

$ uv python find '>=3.11'

By default, uv python find will include Python versions from virtual environments. If a .venv directory is found in the working directory or any of the parent directories or the VIRTUAL_ENV environment variable is set, it will take precedence over any Python executables on the PATH.
To ignore virtual environments, use the --system flag:

$ uv python find --system

But it is not reccomended.

## Discovery of Python versions
When searching for a Python version, the following locations are checked:
	•	Managed Python installations in the UV_PYTHON_INSTALL_DIR.
	•	A Python interpreter on the PATH as python, python3, or python3.x on macOS and Linux, or python.exe on Windows.
	•	On Windows, the Python interpreters in the Windows registry and Microsoft Store Python interpreters (see py --list-paths) that match the requested version.

In some cases, uv allows using a Python version from a virtual environment. In this case, the virtual environment's interpreter will be checked for compatibility with the request before searching for an installation as described above. See the pip-compatible virtual environment discovery documentation for details.
When performing discovery, non-executable files will be ignored. Each discovered executable is queried for metadata to ensure it meets the requested Python version. If the query fails, the executable will be skipped. If the executable satisfies the request, it is used without inspecting additional executables.
When searching for a managed Python version, uv will prefer newer versions first. When searching for a system Python version, uv will use the first compatible version — not the newest version.
If a Python version cannot be found on the system, uv will check for a compatible managed Python version download.

## EXAMPLE OF INSTALLING A VERSION OF PYTHON AND CHANGING IT LATER WITH PIN:

## Install multiple Python versions:

```
$ uv python install 3.10 3.11 3.12

Searching for Python versions matching: Python 3.10

Searching for Python versions matching: Python 3.11

Searching for Python versions matching: Python 3.12

Installed 3 versions in 3.42s

 + cpython-3.10.14-macos-aarch64-none

 + cpython-3.11.9-macos-aarch64-none

 + cpython-3.12.4-macos-aarch64-none
 ```
 
## Download Python versions as needed:

```
$ uv venv --python 3.12.0

Using CPython 3.12.0

Creating virtual environment at: .venv

Activate with: source .venv/bin/activate


$ uv run --python pypy@3.8 -- python

Python 3.8.16 (a9dbdca6fc3286b0addd2240f11d97d8e8de187a, Dec 29 2022, 11:45:30)

[PyPy 7.3.11 with GCC Apple LLVM 13.1.6 (clang-1316.0.21.2.5)] on darwin

Type "help", "copyright", "credits" or "license" for more information.
```

## Change to use a specific Python version in the current directory:

```
$ uv python pin 3.11

Pinned `.python-version` to `3.11`
```

------------------------------------------

# Frontend only
uv run pnpm run dev


### Testing

# All tests (if no dhtl present)
uv run bash runtests.sh

# Python tests only
uv run pytest .
uv run pytest ./tests/test_file.py         # Specific file
uv run pytest ./tests/test_file.py::test_function  # Specific test
uv run pytest -k "test_name"               # By test name pattern
uv run pytest -m "not slow"                # Skip slow tests

# Frontend E2E tests
uv run pnpm run e2e
uv run npx playwright test                        # Alternative
uv run npx playwright test --ui                   # With UI mode


### Code Quality

# Run all linters (pre-commit, ruff, black, mypy, shellcheck, yamllint)
dhtl lint

# Lint with automatic fixes
dhtl lint --fix

# Format all code (uses ruff format, black, isort)
dhtl format

# Check formatting without changes
dhtl format --check

### Code Quality

# Python formatting and linting commands syntax to use internally in dhtl:
uv run ruff format       # format with ruff
uv run ruff check --ignore E203,E402,E501,E266,W505,F841,F842,F401,W293,I001,UP015,C901,W291 --isolated --fix --output-format full
COLUMNS=400 uv run mypy --strict --show-error-context --pretty --install-types --no-color-output --non-interactive --show-error-codes --show-error-code-links --no-error-summary --follow-imports=normal cli_translator.py >mypy_lint_log.txt

# TypeScript/JavaScript formatting and linting commands syntax to use internally in dhtl:
uv run pnpm run lint            # ESLint
uv run pnpm run format          # Prettier
uv run pnpm run check           # Check formatting without fixing

# Bash scripts linting commands syntax to use internally in dhtl:
uv run shellcheck --severity=error --extended-analysis=true  # Shellcheck (always use severity=error!)

# YAML scripts linting
uv run yamllint


### Building and Packaging

# Frontend build
uv run pnpm run build

# Build Python package (includes Electron app)
uv run bash ./install.sh              # Full installation from source
uv init                   # Init package with uv, creating pyproject.toml file, git and others
uv init --python 3.10     # Init package with a specific python version
uv init --app             # Init package with app configuration
uv init --lib             # Init package with library module configuration
uv python install 3.10    # Download and install a specific version of Python runtime
uv python pin 3.10        # Change python version for current venv
uv add <..module..>       # Add module to pyproject.toml dependencies
uv add -r requirements.txt # Add requirements from requirements.txt to pyproject.toml
uv pip install -r requirements.txt # Install dependencies from requirements.txt
uv pip compile <..arguments..> # compile requirement file
uv build                  # Build with uv
uv run python -m build    # Build wheel only

# What uv init generates:
```
.
├── .venv
│   ├── bin
│   ├── lib
│   └── pyvenv.cfg
├── .python-version
├── README.md
├── main.py
├── pyproject.toml
└── uv.lock

```

# What pyproject.toml contains:

```
[project]
name = "hello-world"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
dependencies = []

```

# What the file .python-version contains
The .python-version file contains the project's default Python version. This file tells uv which Python version to use when creating the project's virtual environment.

# What the .venv folder contains
The .venv folder contains your project's virtual environment, a Python environment that is isolated from the rest of your system. This is where uv will install your project's dependencies and binaries.

# What the file uv.lock contains:
uv.lock is a cross-platform lockfile that contains exact information about your project's dependencies. Unlike the pyproject.toml which is used to specify the broad requirements of your project, the lockfile contains the exact resolved versions that are installed in the project environment. This file should be checked into version control, allowing for consistent and reproducible installations across machines.
uv.lock is a human-readable TOML file but is managed by uv and should not be edited manually.

# Install package
uv pip install dist/*.whl    # Install built wheel
uv pip install -e .         # Development install

# Install global uv tools
uv tools install ruff
uv tools install mypy
uv tools install yamllint
uv tools install bump_my_version
...etc.

# Execute globally installed uv tools
uv tools run ruff <..arguments..>
uv tools run mypy <..arguments..>
uv tools run yamllint <..arguments..>
uv tools run bump_my_version <..arguments..>
...etc.


## More detailed list of options for the uv venv command:
Create a virtual environment

Usage: uv venv [OPTIONS] [PATH]

Arguments:
  [PATH]  The path to the virtual environment to create

Options:
      --no-project                           Avoid discovering a project or workspace
      --seed                                 Install seed packages (one or more of: `pip`, `setuptools`, and `wheel`) into the virtual environment [env:
                                             UV_VENV_SEED=]
      --allow-existing                       Preserve any existing files or directories at the target path
      --prompt <PROMPT>                      Provide an alternative prompt prefix for the virtual environment.
      --system-site-packages                 Give the virtual environment access to the system site packages directory
      --relocatable                          Make the virtual environment relocatable
      --index-strategy <INDEX_STRATEGY>      The strategy to use when resolving against multiple index URLs [env: UV_INDEX_STRATEGY=] [possible values:
                                             first-index, unsafe-first-match, unsafe-best-match]
      --keyring-provider <KEYRING_PROVIDER>  Attempt to use `keyring` for authentication for index URLs [env: UV_KEYRING_PROVIDER=] [possible values: disabled,
                                             subprocess]
      --exclude-newer <EXCLUDE_NEWER>        Limit candidate packages to those that were uploaded prior to the given date [env: UV_EXCLUDE_NEWER=]
      --link-mode <LINK_MODE>                The method to use when installing packages from the global cache [env: UV_LINK_MODE=] [possible values: clone, copy,
                                             hardlink, symlink]

Python options:
  -p, --python <PYTHON>      The Python interpreter to use for the virtual environment. [env: UV_PYTHON=]
      --managed-python       Require use of uv-managed Python versions [env: UV_MANAGED_PYTHON=]
      --no-managed-python    Disable use of uv-managed Python versions [env: UV_NO_MANAGED_PYTHON=]
      --no-python-downloads  Disable automatic downloads of Python. [env: "UV_PYTHON_DOWNLOADS=never"]

Index options:
      --index <INDEX>                      The URLs to use when resolving dependencies, in addition to the default index [env: UV_INDEX=]
      --default-index <DEFAULT_INDEX>      The URL of the default package index (by default: <https://pypi.org/simple>) [env: UV_DEFAULT_INDEX=]
  -i, --index-url <INDEX_URL>              (Deprecated: use `--default-index` instead) The URL of the Python package index (by default: <https://pypi.org/simple>)
                                           [env: UV_INDEX_URL=]
      --extra-index-url <EXTRA_INDEX_URL>  (Deprecated: use `--index` instead) Extra URLs of package indexes to use, in addition to `--index-url` [env:
                                           UV_EXTRA_INDEX_URL=]
  -f, --find-links <FIND_LINKS>            Locations to search for candidate distributions, in addition to those found in the registry indexes [env:
                                           UV_FIND_LINKS=]
      --no-index                           Ignore the registry index (e.g., PyPI), instead relying on direct URL dependencies and those provided via `--find-links`

Cache options:
      --refresh                            Refresh all cached data
  -n, --no-cache                           Avoid reading from or writing to the cache, instead using a temporary directory for the duration of the operation [env:
                                           UV_NO_CACHE=]
      --refresh-package <REFRESH_PACKAGE>  Refresh cached data for a specific package
      --cache-dir <CACHE_DIR>              Path to the cache directory [env: UV_CACHE_DIR=]

Global options:
  -q, --quiet...                                   Use quiet output
  -v, --verbose...                                 Use verbose output
      --color <COLOR_CHOICE>                       Control the use of color in output [possible values: auto, always, never]
      --native-tls                                 Whether to load TLS certificates from the platform's native certificate store [env: UV_NATIVE_TLS=]
      --offline                                    Disable network access [env: UV_OFFLINE=]
      --allow-insecure-host <ALLOW_INSECURE_HOST>  Allow insecure connections to a host [env: UV_INSECURE_HOST=]
      --no-progress                                Hide all progress outputs [env: UV_NO_PROGRESS=]
      --directory <DIRECTORY>                      Change to the given directory prior to running the command
      --project <PROJECT>                          Run the command within the given project directory [env: UV_PROJECT=]
      --config-file <CONFIG_FILE>                  The path to a `uv.toml` file to use for configuration [env: UV_CONFIG_FILE=]
      --no-config                                  Avoid discovering configuration files (`pyproject.toml`, `uv.toml`) [env: UV_NO_CONFIG=]
  -h, --help                                       Display the concise help for this command

Use `uv help venv` for more details.


## More detailed list of options for the uv init command:
Create a new project

Usage: uv init [OPTIONS] [PATH]

Arguments:
  [PATH]  The path to use for the project/script

Options:
      --name <NAME>                    The name of the project
      --bare                           Only create a `pyproject.toml`
      --package                        Set up the project to be built as a Python package
      --no-package                     Do not set up the project to be built as a Python package
      --app                            Create a project for an application
      --lib                            Create a project for a library
      --script                         Create a script
      --description <DESCRIPTION>      Set the project description
      --no-description                 Disable the description for the project
      --vcs <VCS>                      Initialize a version control system for the project [possible values: git, none]
      --build-backend <BUILD_BACKEND>  Initialize a build-backend of choice for the project [possible values: hatch, flit, pdm, poetry, setuptools, maturin,
                                       scikit]
      --no-readme                      Do not create a `README.md` file
      --author-from <AUTHOR_FROM>      Fill in the `authors` field in the `pyproject.toml` [possible values: auto, git, none]
      --no-pin-python                  Do not create a `.python-version` file for the project
      --no-workspace                   Avoid discovering a workspace and create a standalone project

Python options:
  -p, --python <PYTHON>      The Python interpreter to use to determine the minimum supported Python version. [env: UV_PYTHON=]
      --managed-python       Require use of uv-managed Python versions [env: UV_MANAGED_PYTHON=]
      --no-managed-python    Disable use of uv-managed Python versions [env: UV_NO_MANAGED_PYTHON=]
      --no-python-downloads  Disable automatic downloads of Python. [env: "UV_PYTHON_DOWNLOADS=never"]

Cache options:
  -n, --no-cache               Avoid reading from or writing to the cache, instead using a temporary directory for the duration of the operation [env:
                               UV_NO_CACHE=]
      --cache-dir <CACHE_DIR>  Path to the cache directory [env: UV_CACHE_DIR=]

Global options:
  -q, --quiet...                                   Use quiet output
  -v, --verbose...                                 Use verbose output
      --color <COLOR_CHOICE>                       Control the use of color in output [possible values: auto, always, never]
      --native-tls                                 Whether to load TLS certificates from the platform's native certificate store [env: UV_NATIVE_TLS=]
      --offline                                    Disable network access [env: UV_OFFLINE=]
      --allow-insecure-host <ALLOW_INSECURE_HOST>  Allow insecure connections to a host [env: UV_INSECURE_HOST=]
      --no-progress                                Hide all progress outputs [env: UV_NO_PROGRESS=]
      --directory <DIRECTORY>                      Change to the given directory prior to running the command
      --project <PROJECT>                          Run the command within the given project directory [env: UV_PROJECT=]
      --config-file <CONFIG_FILE>                  The path to a `uv.toml` file to use for configuration [env: UV_CONFIG_FILE=]
      --no-config                                  Avoid discovering configuration files (`pyproject.toml`, `uv.toml`) [env: UV_NO_CONFIG=]
  -h, --help                                       Display the concise help for this command



## More detailed list of options for uv sync command:
Update the project's environment

Usage: uv sync [OPTIONS]

Options:
      --extra <EXTRA>                            Include optional dependencies from the specified extra name
      --all-extras                               Include all optional dependencies
      --no-extra <NO_EXTRA>                      Exclude the specified optional dependencies, if `--all-extras` is supplied
      --no-dev                                   Disable the development dependency group
      --only-dev                                 Only include the development dependency group
      --group <GROUP>                            Include dependencies from the specified dependency group
      --no-group <NO_GROUP>                      Disable the specified dependency group
      --no-default-groups                        Ignore the default dependency groups
      --only-group <ONLY_GROUP>                  Only include dependencies from the specified dependency group
      --all-groups                               Include dependencies from all dependency groups
      --no-editable                              Install any editable dependencies, including the project and any workspace members, as non-editable [env:
                                                 UV_NO_EDITABLE=]
      --inexact                                  Do not remove extraneous packages present in the environment
      --active                                   Sync dependencies to the active virtual environment
      --no-install-project                       Do not install the current project
      --no-install-workspace                     Do not install any workspace members, including the root project
      --no-install-package <NO_INSTALL_PACKAGE>  Do not install the given package(s)
      --locked                                   Assert that the `uv.lock` will remain unchanged [env: UV_LOCKED=]
      --frozen                                   Sync without updating the `uv.lock` file [env: UV_FROZEN=]
      --dry-run                                  Perform a dry run, without writing the lockfile or modifying the project environment
      --all-packages                             Sync all packages in the workspace
      --package <PACKAGE>                        Sync for a specific package in the workspace
      --script <SCRIPT>                          Sync the environment for a Python script, rather than the current project
      --check                                    Check if the Python environment is synchronized with the project

Index options:
      --index <INDEX>                        The URLs to use when resolving dependencies, in addition to the default index [env: UV_INDEX=]
      --default-index <DEFAULT_INDEX>        The URL of the default package index (by default: <https://pypi.org/simple>) [env: UV_DEFAULT_INDEX=]
  -i, --index-url <INDEX_URL>                (Deprecated: use `--default-index` instead) The URL of the Python package index (by default:
                                             <https://pypi.org/simple>) [env: UV_INDEX_URL=]
      --extra-index-url <EXTRA_INDEX_URL>    (Deprecated: use `--index` instead) Extra URLs of package indexes to use, in addition to `--index-url` [env:
                                             UV_EXTRA_INDEX_URL=]
  -f, --find-links <FIND_LINKS>              Locations to search for candidate distributions, in addition to those found in the registry indexes [env:
                                             UV_FIND_LINKS=]
      --no-index                             Ignore the registry index (e.g., PyPI), instead relying on direct URL dependencies and those provided via
                                             `--find-links`
      --index-strategy <INDEX_STRATEGY>      The strategy to use when resolving against multiple index URLs [env: UV_INDEX_STRATEGY=] [possible values:
                                             first-index, unsafe-first-match, unsafe-best-match]
      --keyring-provider <KEYRING_PROVIDER>  Attempt to use `keyring` for authentication for index URLs [env: UV_KEYRING_PROVIDER=] [possible values: disabled,
                                             subprocess]

Resolver options:
  -U, --upgrade                            Allow package upgrades, ignoring pinned versions in any existing output file. Implies `--refresh`
  -P, --upgrade-package <UPGRADE_PACKAGE>  Allow upgrades for a specific package, ignoring pinned versions in any existing output file. Implies `--refresh-package`
      --resolution <RESOLUTION>            The strategy to use when selecting between the different compatible versions for a given package requirement [env:
                                           UV_RESOLUTION=] [possible values: highest, lowest, lowest-direct]
      --prerelease <PRERELEASE>            The strategy to use when considering pre-release versions [env: UV_PRERELEASE=] [possible values: disallow, allow,
                                           if-necessary, explicit, if-necessary-or-explicit]
      --fork-strategy <FORK_STRATEGY>      The strategy to use when selecting multiple versions of a given package across Python versions and platforms [env:
                                           UV_FORK_STRATEGY=] [possible values: fewest, requires-python]
      --exclude-newer <EXCLUDE_NEWER>      Limit candidate packages to those that were uploaded prior to the given date [env: UV_EXCLUDE_NEWER=]
      --no-sources                         Ignore the `tool.uv.sources` table when resolving dependencies. Used to lock against the standards-compliant,
                                           publishable package metadata, as opposed to using any workspace, Git, URL, or local path sources

Installer options:
      --reinstall                              Reinstall all packages, regardless of whether they're already installed. Implies `--refresh`
      --reinstall-package <REINSTALL_PACKAGE>  Reinstall a specific package, regardless of whether it's already installed. Implies `--refresh-package`
      --link-mode <LINK_MODE>                  The method to use when installing packages from the global cache [env: UV_LINK_MODE=] [possible values: clone, copy,
                                               hardlink, symlink]
      --compile-bytecode                       Compile Python files to bytecode after installation [env: UV_COMPILE_BYTECODE=]

Build options:
  -C, --config-setting <CONFIG_SETTING>                          Settings to pass to the PEP 517 build backend, specified as `KEY=VALUE` pairs
      --no-build-isolation                                       Disable isolation when building source distributions [env: UV_NO_BUILD_ISOLATION=]
      --no-build-isolation-package <NO_BUILD_ISOLATION_PACKAGE>  Disable isolation when building source distributions for a specific package
      --no-build                                                 Don't build source distributions [env: UV_NO_BUILD=]
      --no-build-package <NO_BUILD_PACKAGE>                      Don't build source distributions for a specific package [env: UV_NO_BUILD_PACKAGE=]
      --no-binary                                                Don't install pre-built wheels [env: UV_NO_BINARY=]
      --no-binary-package <NO_BINARY_PACKAGE>                    Don't install pre-built wheels for a specific package [env: UV_NO_BINARY_PACKAGE=]

Cache options:
  -n, --no-cache                           Avoid reading from or writing to the cache, instead using a temporary directory for the duration of the operation [env:
                                           UV_NO_CACHE=]
      --cache-dir <CACHE_DIR>              Path to the cache directory [env: UV_CACHE_DIR=]
      --refresh                            Refresh all cached data
      --refresh-package <REFRESH_PACKAGE>  Refresh cached data for a specific package

Python options:
  -p, --python <PYTHON>      The Python interpreter to use for the project environment. [env: UV_PYTHON=]
      --managed-python       Require use of uv-managed Python versions [env: UV_MANAGED_PYTHON=]
      --no-managed-python    Disable use of uv-managed Python versions [env: UV_NO_MANAGED_PYTHON=]
      --no-python-downloads  Disable automatic downloads of Python. [env: "UV_PYTHON_DOWNLOADS=never"]

Global options:
  -q, --quiet...                                   Use quiet output
  -v, --verbose...                                 Use verbose output
      --color <COLOR_CHOICE>                       Control the use of color in output [possible values: auto, always, never]
      --native-tls                                 Whether to load TLS certificates from the platform's native certificate store [env: UV_NATIVE_TLS=]
      --offline                                    Disable network access [env: UV_OFFLINE=]
      --allow-insecure-host <ALLOW_INSECURE_HOST>  Allow insecure connections to a host [env: UV_INSECURE_HOST=]
      --no-progress                                Hide all progress outputs [env: UV_NO_PROGRESS=]
      --directory <DIRECTORY>                      Change to the given directory prior to running the command
      --project <PROJECT>                          Run the command within the given project directory [env: UV_PROJECT=]
      --config-file <CONFIG_FILE>                  The path to a `uv.toml` file to use for configuration [env: UV_CONFIG_FILE=]
      --no-config                                  Avoid discovering configuration files (`pyproject.toml`, `uv.toml`) [env: UV_NO_CONFIG=]
  -h, --help                                       Display the concise help for this command

Use `uv help sync` for more details.


## More detailed list of options for the uv python command:
Manage Python versions and installations

Usage: uv python [OPTIONS] <COMMAND>

Commands:
  list       List the available Python installations
  install    Download and install Python versions
  find       Search for a Python installation
  pin        Pin to a specific Python version
  dir        Show the uv Python installation directory
  uninstall  Uninstall Python versions

Cache options:
  -n, --no-cache               Avoid reading from or writing to the cache, instead using a temporary directory for the duration of the operation [env:
                               UV_NO_CACHE=]
      --cache-dir <CACHE_DIR>  Path to the cache directory [env: UV_CACHE_DIR=]

Python options:
      --managed-python       Require use of uv-managed Python versions [env: UV_MANAGED_PYTHON=]
      --no-managed-python    Disable use of uv-managed Python versions [env: UV_NO_MANAGED_PYTHON=]
      --no-python-downloads  Disable automatic downloads of Python. [env: "UV_PYTHON_DOWNLOADS=never"]

Global options:
  -q, --quiet...                                   Use quiet output
  -v, --verbose...                                 Use verbose output
      --color <COLOR_CHOICE>                       Control the use of color in output [possible values: auto, always, never]
      --native-tls                                 Whether to load TLS certificates from the platform's native certificate store [env: UV_NATIVE_TLS=]
      --offline                                    Disable network access [env: UV_OFFLINE=]
      --allow-insecure-host <ALLOW_INSECURE_HOST>  Allow insecure connections to a host [env: UV_INSECURE_HOST=]
      --no-progress                                Hide all progress outputs [env: UV_NO_PROGRESS=]
      --directory <DIRECTORY>                      Change to the given directory prior to running the command
      --project <PROJECT>                          Run the command within the given project directory [env: UV_PROJECT=]
      --config-file <CONFIG_FILE>                  The path to a `uv.toml` file to use for configuration [env: UV_CONFIG_FILE=]
      --no-config                                  Avoid discovering configuration files (`pyproject.toml`, `uv.toml`) [env: UV_NO_CONFIG=]
  -h, --help                                       Display the concise help for this command

Use `uv help python` for more details.


## More detailed list of options for the uv pip command:
Manage Python packages with a pip-compatible interface

Usage: uv pip [OPTIONS] <COMMAND>

Commands:
  compile    Compile a `requirements.in` file to a `requirements.txt` or `pylock.toml` file
  sync       Sync an environment with a `requirements.txt` or `pylock.toml` file
  install    Install packages into an environment
  uninstall  Uninstall packages from an environment
  freeze     List, in requirements format, packages installed in an environment
  list       List, in tabular format, packages installed in an environment
  show       Show information about one or more installed packages
  tree       Display the dependency tree for an environment
  check      Verify installed packages have compatible dependencies

Cache options:
  -n, --no-cache               Avoid reading from or writing to the cache, instead using a temporary directory for the duration of the operation [env:
                               UV_NO_CACHE=]
      --cache-dir <CACHE_DIR>  Path to the cache directory [env: UV_CACHE_DIR=]

Python options:
      --managed-python       Require use of uv-managed Python versions [env: UV_MANAGED_PYTHON=]
      --no-managed-python    Disable use of uv-managed Python versions [env: UV_NO_MANAGED_PYTHON=]
      --no-python-downloads  Disable automatic downloads of Python. [env: "UV_PYTHON_DOWNLOADS=never"]

Global options:
  -q, --quiet...                                   Use quiet output
  -v, --verbose...                                 Use verbose output
      --color <COLOR_CHOICE>                       Control the use of color in output [possible values: auto, always, never]
      --native-tls                                 Whether to load TLS certificates from the platform's native certificate store [env: UV_NATIVE_TLS=]
      --offline                                    Disable network access [env: UV_OFFLINE=]
      --allow-insecure-host <ALLOW_INSECURE_HOST>  Allow insecure connections to a host [env: UV_INSECURE_HOST=]
      --no-progress                                Hide all progress outputs [env: UV_NO_PROGRESS=]
      --directory <DIRECTORY>                      Change to the given directory prior to running the command
      --project <PROJECT>                          Run the command within the given project directory [env: UV_PROJECT=]
      --config-file <CONFIG_FILE>                  The path to a `uv.toml` file to use for configuration [env: UV_CONFIG_FILE=]
      --no-config                                  Avoid discovering configuration files (`pyproject.toml`, `uv.toml`) [env: UV_NO_CONFIG=]
  -h, --help                                       Display the concise help for this command

Use `uv help pip` for more details.



## More detailed list of options for uv build command:
Build Python packages into source distributions and wheels

Usage: uv build [OPTIONS] [SRC]

Arguments:
  [SRC]  The directory from which distributions should be built, or a source distribution archive to build into a wheel

Options:
      --package <PACKAGE>                      Build a specific package in the workspace
      --all-packages                           Builds all packages in the workspace
  -o, --out-dir <OUT_DIR>                      The output directory to which distributions should be written
      --sdist                                  Build a source distribution ("sdist") from the given directory
      --wheel                                  Build a binary distribution ("wheel") from the given directory
      --no-build-logs                          Hide logs from the build backend
      --force-pep517                           Always build through PEP 517, don't use the fast path for the uv build backend
  -b, --build-constraints <BUILD_CONSTRAINTS>  Constrain build dependencies using the given requirements files when building distributions [env:
                                               UV_BUILD_CONSTRAINT=]
      --require-hashes                         Require a matching hash for each requirement [env: UV_REQUIRE_HASHES=]
      --no-verify-hashes                       Disable validation of hashes in the requirements file [env: UV_NO_VERIFY_HASHES=]

Python options:
  -p, --python <PYTHON>      The Python interpreter to use for the build environment. [env: UV_PYTHON=]
      --managed-python       Require use of uv-managed Python versions [env: UV_MANAGED_PYTHON=]
      --no-managed-python    Disable use of uv-managed Python versions [env: UV_NO_MANAGED_PYTHON=]
      --no-python-downloads  Disable automatic downloads of Python. [env: "UV_PYTHON_DOWNLOADS=never"]

Index options:
      --index <INDEX>                        The URLs to use when resolving dependencies, in addition to the default index [env: UV_INDEX=]
      --default-index <DEFAULT_INDEX>        The URL of the default package index (by default: <https://pypi.org/simple>) [env: UV_DEFAULT_INDEX=]
  -i, --index-url <INDEX_URL>                (Deprecated: use `--default-index` instead) The URL of the Python package index (by default:
                                             <https://pypi.org/simple>) [env: UV_INDEX_URL=]
      --extra-index-url <EXTRA_INDEX_URL>    (Deprecated: use `--index` instead) Extra URLs of package indexes to use, in addition to `--index-url` [env:
                                             UV_EXTRA_INDEX_URL=]
  -f, --find-links <FIND_LINKS>              Locations to search for candidate distributions, in addition to those found in the registry indexes [env:
                                             UV_FIND_LINKS=]
      --no-index                             Ignore the registry index (e.g., PyPI), instead relying on direct URL dependencies and those provided via
                                             `--find-links`
      --index-strategy <INDEX_STRATEGY>      The strategy to use when resolving against multiple index URLs [env: UV_INDEX_STRATEGY=] [possible values:
                                             first-index, unsafe-first-match, unsafe-best-match]
      --keyring-provider <KEYRING_PROVIDER>  Attempt to use `keyring` for authentication for index URLs [env: UV_KEYRING_PROVIDER=] [possible values: disabled,
                                             subprocess]

Resolver options:
  -U, --upgrade                            Allow package upgrades, ignoring pinned versions in any existing output file. Implies `--refresh`
  -P, --upgrade-package <UPGRADE_PACKAGE>  Allow upgrades for a specific package, ignoring pinned versions in any existing output file. Implies `--refresh-package`
      --resolution <RESOLUTION>            The strategy to use when selecting between the different compatible versions for a given package requirement [env:
                                           UV_RESOLUTION=] [possible values: highest, lowest, lowest-direct]
      --prerelease <PRERELEASE>            The strategy to use when considering pre-release versions [env: UV_PRERELEASE=] [possible values: disallow, allow,
                                           if-necessary, explicit, if-necessary-or-explicit]
      --fork-strategy <FORK_STRATEGY>      The strategy to use when selecting multiple versions of a given package across Python versions and platforms [env:
                                           UV_FORK_STRATEGY=] [possible values: fewest, requires-python]
      --exclude-newer <EXCLUDE_NEWER>      Limit candidate packages to those that were uploaded prior to the given date [env: UV_EXCLUDE_NEWER=]
      --no-sources                         Ignore the `tool.uv.sources` table when resolving dependencies. Used to lock against the standards-compliant,
                                           publishable package metadata, as opposed to using any workspace, Git, URL, or local path sources

Build options:
  -C, --config-setting <CONFIG_SETTING>                          Settings to pass to the PEP 517 build backend, specified as `KEY=VALUE` pairs
      --no-build-isolation                                       Disable isolation when building source distributions [env: UV_NO_BUILD_ISOLATION=]
      --no-build-isolation-package <NO_BUILD_ISOLATION_PACKAGE>  Disable isolation when building source distributions for a specific package
      --no-build                                                 Don't build source distributions [env: UV_NO_BUILD=]
      --no-build-package <NO_BUILD_PACKAGE>                      Don't build source distributions for a specific package [env: UV_NO_BUILD_PACKAGE=]
      --no-binary                                                Don't install pre-built wheels [env: UV_NO_BINARY=]
      --no-binary-package <NO_BINARY_PACKAGE>                    Don't install pre-built wheels for a specific package [env: UV_NO_BINARY_PACKAGE=]

Installer options:
      --link-mode <LINK_MODE>  The method to use when installing packages from the global cache [env: UV_LINK_MODE=] [possible values: clone, copy, hardlink,
                               symlink]

Cache options:
  -n, --no-cache                           Avoid reading from or writing to the cache, instead using a temporary directory for the duration of the operation [env:
                                           UV_NO_CACHE=]
      --cache-dir <CACHE_DIR>              Path to the cache directory [env: UV_CACHE_DIR=]
      --refresh                            Refresh all cached data
      --refresh-package <REFRESH_PACKAGE>  Refresh cached data for a specific package

Global options:
  -q, --quiet...                                   Use quiet output
  -v, --verbose...                                 Use verbose output
      --color <COLOR_CHOICE>                       Control the use of color in output [possible values: auto, always, never]
      --native-tls                                 Whether to load TLS certificates from the platform's native certificate store [env: UV_NATIVE_TLS=]
      --offline                                    Disable network access [env: UV_OFFLINE=]
      --allow-insecure-host <ALLOW_INSECURE_HOST>  Allow insecure connections to a host [env: UV_INSECURE_HOST=]
      --no-progress                                Hide all progress outputs [env: UV_NO_PROGRESS=]
      --directory <DIRECTORY>                      Change to the given directory prior to running the command
      --project <PROJECT>                          Run the command within the given project directory [env: UV_PROJECT=]
      --config-file <CONFIG_FILE>                  The path to a `uv.toml` file to use for configuration [env: UV_CONFIG_FILE=]
      --no-config                                  Avoid discovering configuration files (`pyproject.toml`, `uv.toml`) [env: UV_NO_CONFIG=]
  -h, --help                                       Display the concise help for this command

Use `uv help build` for more details.


## More detailed list of options for the uv run command:
Run a command or script

Usage: uv run [OPTIONS] [COMMAND]

Options:
      --extra <EXTRA>                          Include optional dependencies from the specified extra name
      --all-extras                             Include all optional dependencies
      --no-extra <NO_EXTRA>                    Exclude the specified optional dependencies, if `--all-extras` is supplied
      --no-dev                                 Disable the development dependency group
      --group <GROUP>                          Include dependencies from the specified dependency group
      --no-group <NO_GROUP>                    Disable the specified dependency group
      --no-default-groups                      Ignore the default dependency groups
      --only-group <ONLY_GROUP>                Only include dependencies from the specified dependency group
      --all-groups                             Include dependencies from all dependency groups
  -m, --module                                 Run a Python module
      --only-dev                               Only include the development dependency group
      --no-editable                            Install any editable dependencies, including the project and any workspace members, as non-editable [env:
                                               UV_NO_EDITABLE=]
      --exact                                  Perform an exact sync, removing extraneous packages
      --env-file <ENV_FILE>                    Load environment variables from a `.env` file [env: UV_ENV_FILE=]
      --no-env-file                            Avoid reading environment variables from a `.env` file [env: UV_NO_ENV_FILE=]
      --with <WITH>                            Run with the given packages installed
      --with-editable <WITH_EDITABLE>          Run with the given packages installed in editable mode
      --with-requirements <WITH_REQUIREMENTS>  Run with all packages listed in the given `requirements.txt` files
      --isolated                               Run the command in an isolated virtual environment
      --active                                 Prefer the active virtual environment over the project's virtual environment
      --no-sync                                Avoid syncing the virtual environment [env: UV_NO_SYNC=]
      --locked                                 Assert that the `uv.lock` will remain unchanged [env: UV_LOCKED=]
      --frozen                                 Run without updating the `uv.lock` file [env: UV_FROZEN=]
  -s, --script                                 Run the given path as a Python script
      --gui-script                             Run the given path as a Python GUI script
      --all-packages                           Run the command with all workspace members installed
      --package <PACKAGE>                      Run the command in a specific package in the workspace
      --no-project                             Avoid discovering the project or workspace

Index options:
      --index <INDEX>                        The URLs to use when resolving dependencies, in addition to the default index [env: UV_INDEX=]
      --default-index <DEFAULT_INDEX>        The URL of the default package index (by default: <https://pypi.org/simple>) [env: UV_DEFAULT_INDEX=]
  -i, --index-url <INDEX_URL>                (Deprecated: use `--default-index` instead) The URL of the Python package index (by default:
                                             <https://pypi.org/simple>) [env: UV_INDEX_URL=]
      --extra-index-url <EXTRA_INDEX_URL>    (Deprecated: use `--index` instead) Extra URLs of package indexes to use, in addition to `--index-url` [env:
                                             UV_EXTRA_INDEX_URL=]
  -f, --find-links <FIND_LINKS>              Locations to search for candidate distributions, in addition to those found in the registry indexes [env:
                                             UV_FIND_LINKS=]
      --no-index                             Ignore the registry index (e.g., PyPI), instead relying on direct URL dependencies and those provided via
                                             `--find-links`
      --index-strategy <INDEX_STRATEGY>      The strategy to use when resolving against multiple index URLs [env: UV_INDEX_STRATEGY=] [possible values:
                                             first-index, unsafe-first-match, unsafe-best-match]
      --keyring-provider <KEYRING_PROVIDER>  Attempt to use `keyring` for authentication for index URLs [env: UV_KEYRING_PROVIDER=] [possible values: disabled,
                                             subprocess]

Resolver options:
  -U, --upgrade                            Allow package upgrades, ignoring pinned versions in any existing output file. Implies `--refresh`
  -P, --upgrade-package <UPGRADE_PACKAGE>  Allow upgrades for a specific package, ignoring pinned versions in any existing output file. Implies `--refresh-package`
      --resolution <RESOLUTION>            The strategy to use when selecting between the different compatible versions for a given package requirement [env:
                                           UV_RESOLUTION=] [possible values: highest, lowest, lowest-direct]
      --prerelease <PRERELEASE>            The strategy to use when considering pre-release versions [env: UV_PRERELEASE=] [possible values: disallow, allow,
                                           if-necessary, explicit, if-necessary-or-explicit]
      --fork-strategy <FORK_STRATEGY>      The strategy to use when selecting multiple versions of a given package across Python versions and platforms [env:
                                           UV_FORK_STRATEGY=] [possible values: fewest, requires-python]
      --exclude-newer <EXCLUDE_NEWER>      Limit candidate packages to those that were uploaded prior to the given date [env: UV_EXCLUDE_NEWER=]
      --no-sources                         Ignore the `tool.uv.sources` table when resolving dependencies. Used to lock against the standards-compliant,
                                           publishable package metadata, as opposed to using any workspace, Git, URL, or local path sources

Installer options:
      --reinstall                              Reinstall all packages, regardless of whether they're already installed. Implies `--refresh`
      --reinstall-package <REINSTALL_PACKAGE>  Reinstall a specific package, regardless of whether it's already installed. Implies `--refresh-package`
      --link-mode <LINK_MODE>                  The method to use when installing packages from the global cache [env: UV_LINK_MODE=] [possible values: clone, copy,
                                               hardlink, symlink]
      --compile-bytecode                       Compile Python files to bytecode after installation [env: UV_COMPILE_BYTECODE=]

Build options:
  -C, --config-setting <CONFIG_SETTING>                          Settings to pass to the PEP 517 build backend, specified as `KEY=VALUE` pairs
      --no-build-isolation                                       Disable isolation when building source distributions [env: UV_NO_BUILD_ISOLATION=]
      --no-build-isolation-package <NO_BUILD_ISOLATION_PACKAGE>  Disable isolation when building source distributions for a specific package
      --no-build                                                 Don't build source distributions [env: UV_NO_BUILD=]
      --no-build-package <NO_BUILD_PACKAGE>                      Don't build source distributions for a specific package [env: UV_NO_BUILD_PACKAGE=]
      --no-binary                                                Don't install pre-built wheels [env: UV_NO_BINARY=]
      --no-binary-package <NO_BINARY_PACKAGE>                    Don't install pre-built wheels for a specific package [env: UV_NO_BINARY_PACKAGE=]

Cache options:
  -n, --no-cache                           Avoid reading from or writing to the cache, instead using a temporary directory for the duration of the operation [env:
                                           UV_NO_CACHE=]
      --cache-dir <CACHE_DIR>              Path to the cache directory [env: UV_CACHE_DIR=]
      --refresh                            Refresh all cached data
      --refresh-package <REFRESH_PACKAGE>  Refresh cached data for a specific package

Python options:
  -p, --python <PYTHON>      The Python interpreter to use for the run environment. [env: UV_PYTHON=]
      --managed-python       Require use of uv-managed Python versions [env: UV_MANAGED_PYTHON=]
      --no-managed-python    Disable use of uv-managed Python versions [env: UV_NO_MANAGED_PYTHON=]
      --no-python-downloads  Disable automatic downloads of Python. [env: "UV_PYTHON_DOWNLOADS=never"]

Global options:
  -q, --quiet...                                   Use quiet output
  -v, --verbose...                                 Use verbose output
      --color <COLOR_CHOICE>                       Control the use of color in output [possible values: auto, always, never]
      --native-tls                                 Whether to load TLS certificates from the platform's native certificate store [env: UV_NATIVE_TLS=]
      --offline                                    Disable network access [env: UV_OFFLINE=]
      --allow-insecure-host <ALLOW_INSECURE_HOST>  Allow insecure connections to a host [env: UV_INSECURE_HOST=]
      --no-progress                                Hide all progress outputs [env: UV_NO_PROGRESS=]
      --directory <DIRECTORY>                      Change to the given directory prior to running the command
      --project <PROJECT>                          Run the command within the given project directory [env: UV_PROJECT=]
      --config-file <CONFIG_FILE>                  The path to a `uv.toml` file to use for configuration [env: UV_CONFIG_FILE=]
      --no-config                                  Avoid discovering configuration files (`pyproject.toml`, `uv.toml`) [env: UV_NO_CONFIG=]
  -h, --help                                       Display the concise help for this command

Use `uv help run` for more details.


### Running AtlasVibe
```bash
# After installation via pip
atlasvibe                    # Run full application
atlasvibe server             # Run backend server only
atlasvibe ui                 # Run UI only
atlasvibe ui --dev          # Run UI in development mode
atlasvibe init my-project    # Create new project

# Development mode (without installation)
uv run python main.py        # Run backend
pnpm run dev                 # Run frontend (separate terminal)
```

### Block Management
```bash
# Sync Python blocks (regenerate manifests)
just sync                # or: uv run python3 fjblock.py sync

# Add new blocks from a directory
just add <path>          # or: uv run python3 fjblock.py add <path>

# Initialize docs and blocks
just init
```

## Package Structure (NEW)

AtlasVibe is now distributed as a standard Python package that includes both backend and frontend:

### No More ASAR Packaging
- Electron app is distributed unpacked (asar: false)
- Simplifies file access and debugging
- No more path resolution issues with process.resourcesPath
- All files are directly accessible in the installed package

### Unified Distribution
- Single `pip install atlasvibe` installs everything
- No need for platform-specific Electron builds
- Python backend and Electron frontend in same package
- Simplified deployment and version management

### Installation Methods
1. **From Source**: `./install.sh` - builds and installs complete package
2. **From PyPI**: `pip install atlasvibe` (when published)
3. **Development**: `pip install -e .` for editable install

## Architecture Overview

AtlasVibe is a visual programming IDE for Python, consisting of three main components:

### 1. Frontend (Electron + React + TypeScript)
- **Entry Point**: `/src/main/index.ts` (Electron main process)
- **UI Components**: `/src/renderer/` (React application)
  - `/components/` - Reusable UI components
  - `/routes/` - Page-level components (flow chart, control panel, etc.)
  - `/stores/` - Zustand state management
  - `/hooks/` - Custom React hooks
  - `/lib/` - Utility functions and API clients
- **Key Technologies**:
  - ReactFlow for visual programming canvas
  - Plotly for data visualization
  - TailwindCSS for styling
  - Zustand for state management

### 2. Backend (Python FastAPI Server)
- **Entry Point**: `/main.py`
- **Application Code**: `/captain/`
  - `/routes/` - API endpoints (blocks, flowchart, devices, etc.)
  - `/services/` - Business logic layer
  - `/models/` - Pydantic models for data validation
  - `/types/` - TypeScript-compatible type definitions
  - `/utils/` - Helper functions and utilities
- **Key Technologies**:
  - FastAPI for REST API
  - Prefect for workflow orchestration
  - WebSocket for real-time communication
  - Pydantic for data validation

### 3. Block System
- **Blueprint Blocks**: `/blocks/` - Organized by category (AI_ML, DSP, MATH, etc.)
- **Block Structure**:
  ```
  blocks/CATEGORY/SUBCATEGORY/BLOCK_NAME/
  ├── BLOCK_NAME.py          # Main implementation with @atlasvibe decorator
  ├── app.json               # UI metadata (position, color, etc.)
  ├── block_data.json        # Parameter definitions
  ├── example.md             # Documentation
  ├── requirements.txt       # Optional dependencies
  └── *_test_.py             # Unit tests
  ```
- **SDKs**:
  - `/pkgs/atlasvibe_sdk/` - Core SDK for block development
  - `/pkgs/atlasvibe/` - Legacy SDK (contains DataContainer, node decorators)

## Key Architectural Patterns

### Block Execution Flow
1. User creates visual flow in ReactFlow canvas
2. Frontend sends topology to backend via `/blocks/run` API
3. Backend creates Prefect flow from topology
4. Worker processes execute blocks in dependency order
5. Results stream back via WebSocket to frontend
6. Frontend renders results using appropriate visualizations

### Data Flow Between Blocks
- Blocks communicate via `DataContainer` objects
- DataContainer wraps various data types (scalar, vector, matrix, dataframe, etc.)
- Serialization handled automatically between processes
- Results cached using joblib for performance

### Dynamic Block Discovery
- On startup, `captain/utils/import_blocks.py` scans `/blocks/` directory
- Manifest generator (`captain/utils/manifest/`) extracts metadata from Python decorators
- Block registry maintained in memory for fast lookup
- Frontend fetches available blocks via `/blocks` API

### WebSocket Communication Protocol
- Connection established at `/ws`
- Message types: WORKER_STARTED, BLOCK_STARTED, BLOCK_FINISHED, JOB_STARTED, etc.
- Enables real-time progress tracking and result streaming

## Important Development Patterns

### Adding New API Endpoints
1. Define Pydantic models in `/captain/models/`
2. Create TypeScript types in `/captain/types/`
3. Implement endpoint in `/captain/routes/`
4. Update frontend API client in `/src/lib/api.ts`

### Creating New Blocks
1. Create directory structure under appropriate category in `/blocks/`
2. Implement block function with `@atlasvibe` decorator
3. Define parameters in docstring and decorator
4. Run `just sync` to regenerate manifests
5. Block automatically appears in UI

### State Management
- Zustand stores in `/src/renderer/stores/`:
  - `app.ts` - Application-wide state
  - `flowchart.ts` - Visual flow editor state
  - `socket.ts` - WebSocket connection state
  - `project.ts` - Project management state
- Follow pattern of actions as methods, state as properties

### Testing Patterns
- Python blocks: Place `*_test_.py` files alongside block implementation
- Backend API: Tests in `/captain/tests/`
- Frontend components: Tests in `/tests/`
- E2E tests: Playwright tests in `/playwright-test/`

## Current Development Focus

The project is transitioning from hardware test sequencer to general-purpose visual IDE:
1. **Project-Centric Blocks**: Moving from global blocks to per-project custom blocks
2. **In-IDE Editing**: Enabling code editing within the application
3. **AI Agent Capabilities**: Future goal for self-modifying blocks

See DEVELOPMENT_PLAN.md for detailed roadmap.

## Testing Best Practices

### Avoid Unnecessary Mocks
- **CRITICAL**: Mocks should be used ONLY when it is impossible to test otherwise (e.g., external services, hardware dependencies)
- Mocks can mask real functionality and hide bugs - prefer real integration tests
- When testing file operations, use real temporary directories and files instead of mocking the filesystem
- When testing API endpoints, use TestClient with the actual FastAPI app instead of mocking HTTP calls
- For database operations, use a test database or in-memory database instead of mocking

### Building and Running Tests
- **Before running Playwright tests**: The application MUST be built first
  ```bash
  pnpm run build
  pnpm run electron-package:mac  # or :windows/:linux
  ```
- Install all dependencies before testing:
  ```bash
  pnpm install  # For Node.js dependencies
  uv sync --all-extras  # For Python dependencies
  ```
- For Python packages in development, install them:
  ```bash
  cd pkgs/atlasvibe && uv pip install -e .
  ```

### Test Organization
- Unit tests: Test individual functions with minimal dependencies
- Integration tests: Test complete workflows with real components
- E2E tests: Test the full application behavior from user perspective
- Always prefer integration tests over unit tests with heavy mocking

### Example of Good Testing Practice
```python
# GOOD: Real file operations
def test_update_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "test.txt"
        file_path.write_text("original")
        
        # Test actual file update
        update_file(file_path, "new content")
        assert file_path.read_text() == "new content"

# BAD: Mocking file operations
def test_update_file_with_mock():
    mock_path = Mock()
    mock_path.read_text.return_value = "original"
    
    # This doesn't test real file behavior
    update_file(mock_path, "new content")
    mock_path.write_text.assert_called_with("new content")
```

### Running Tests in CI/CD
- Set up environment variables properly
- Ensure all dependencies are installed
- Build the application before E2E tests
- Use headless mode for Playwright tests in CI

## Block Metadata Generation and Regeneration

### Overview
AtlasVibe blocks require metadata files for proper functioning. When a block's Python file is created or modified, various metadata files are generated or must be created manually.

### Block File Structure
```
blocks/CATEGORY/SUBCATEGORY/BLOCK_NAME/
├── BLOCK_NAME.py          # Python implementation (required)
├── block_data.json        # Docstring metadata (auto-generated)
├── app.json               # Example workflow (manual)
├── example.md             # Example description (manual)
├── BLOCK_NAME_test.py     # Unit tests (manual)
└── __pycache__/           # Python bytecode (auto-generated)
```

### Automatic Metadata Generation

#### 1. Manifest Generation (In-Memory)
- **Function**: `captain/utils/manifest/build_manifest.py::create_manifest()`
- **Trigger**: Called when blocks are loaded or updated
- **Process**:
  1. Parses the Python AST (Abstract Syntax Tree)
  2. Extracts function signature, parameters, and return types
  3. Recognizes both `@atlasvibe` and `@atlasvibe_node` decorators
  4. Extracts pip dependencies from decorator arguments
  5. Returns manifest with inputs, outputs, parameters, and dependencies

#### 2. Automatic File Generation for Custom Blocks (NEW)
- **Module**: `captain/utils/block_metadata_generator.py`
- **Integration Points**:
  - `/blocks/create-custom/` API (when cloning blueprints)
  - `/blocks/update-code/` API (when editing block code)
  - BlocksWatcher (fallback for direct file changes)
- **Process**:
  1. When blueprint is cloned: Regenerates `block_data.json` from updated function
  2. When code is edited: Regenerates `block_data.json` from modified docstring
  3. BlocksWatcher: Detects external file changes and triggers regeneration
- **Integration**: Seamlessly integrated into AtlasVibe's clone-and-edit workflow

#### 3. block_data.json Generation
- **Function**: `captain/utils/block_metadata_generator.py::generate_block_data_json()`
- **Trigger**: 
  - Automatically when Python file is created/modified
  - Manually via `just sync` or `uv run python3 fjblock.py sync`
- **Process**:
  1. Parses Python file with matching folder name
  2. Extracts docstring using `docstring_parser`
  3. Validates NumPy-style docstring format
  4. Preserves existing JSON data while updating docstring
  5. Writes structured JSON with descriptions, parameters, and returns

**Example block_data.json structure**:
```json
{
  "docstring": {
    "short_description": "Append a single data point to an array.",
    "long_description": "The large array must be passed...",
    "parameters": [
      {
        "name": "primary_dp",
        "type": "OrderedPair|Vector|Scalar|Matrix|DataFrame|None",
        "description": "Input that ends up \"on top\" of the resulting DataContainer."
      }
    ],
    "returns": [
      {
        "name": null,
        "type": "OrderedPair, Matrix, DataFrame, Vector",
        "description": null
      }
    ]
  }
}
```

### Metadata File Details

#### 1. app.json
- **Purpose**: Contains a complete example workflow demonstrating the block
- **Content**: ReactFlow nodes and edges showing how to use the block
- **Generation**: Auto-generated with basic template when block is created
- **Customization**: Should be manually updated to show meaningful examples

#### 2. example.md
- **Purpose**: Human-readable description of what the example does
- **Content**: Markdown explaining the example workflow
- **Generation**: Auto-generated with template based on docstring
- **Customization**: Should be manually enhanced with detailed examples

#### 3. *_test_.py
- **Purpose**: Unit tests for the block
- **Content**: Test file with basic structure and TODOs
- **Generation**: Auto-generated with test template
- **Customization**: Must be manually implemented with actual tests

#### 4. block_data.json
- **Purpose**: Structured metadata from docstring
- **Content**: Parameters, returns, and descriptions
- **Generation**: Fully automatic from docstring
- **Updates**: Regenerated automatically when Python file changes

### File Watching and Regeneration

#### Backend File Watcher
- **Service**: `captain/services/consumer/blocks_watcher.py::BlocksWatcher`
- **Technology**: Uses `watchfiles` library for async file monitoring
- **Monitors**: 
  - Blueprint blocks directory (`/blocks/`)
  - Project-specific blocks (`project_dir/atlasvibe_blocks/`)
- **On Change**: Broadcasts `{"type": "manifest_update"}` via WebSocket

#### Frontend Response
- **Handler**: `src/renderer/socket-receiver.tsx`
- **Actions on `manifest_update`**:
  1. Shows toast: "Changes detected, syncing blocks with changes..."
  2. Calls `fetchManifest()` to get updated block list
  3. Calls `importCustomBlocks()` for project blocks
  4. Sets `manifestChanged` flag in store

### AtlasVibe Block System Architecture

AtlasVibe uses a sophisticated **blueprint → instance** model where blocks exist in two completely separate layers:

#### Key Concepts:

1. **Blueprint Blocks** (Global Palette):
   - Original blocks in `/blocks/` directory
   - User-created blueprints (saved via "Save this block as a blueprint")
   - **Global and shared across all projects/workflows**
   - **Cannot be directly edited** - must edit an instance and re-save as blueprint
   - Stored in global blocks folder

2. **Block Instances** (Project-specific):
   - **Workflows contain only instances, never blueprints directly**
   - Created when blueprint is dragged from palette to workflow
   - Stored in project's `atlasvibe_blocks/` directory
   - Named as `<blueprint_name>_<instance_index>` (e.g., "ADDITION_1", "ADDITION_2")
   - **Completely decoupled** from blueprint after creation
   - Can be edited, renamed, deleted without affecting blueprint or other instances

#### Block Creation Workflow:

1. **Create Instance from Blueprint** (UI Drag & Drop):
   - User drags blueprint from global palette to workflow
   - System automatically:
     - Clones blueprint to project's `atlasvibe_blocks/` folder
     - Names it `<blueprint_name>_<index>` (auto-incrementing)
     - Places the instance in workflow
     - **Instance is now completely independent**
   - API: `/blocks/create-custom/`

2. **Edit Block Instance** (Integrated UI Editor):
   - User opens instance editor in UI
   - Modifies Python code directly (only affects this instance)
   - Saves changes via `/blocks/update-code/` API
   - System automatically:
     - Updates the instance's Python file
     - Regenerates metadata for this instance only
     - Updates workflow in real-time
     - **Blueprint remains unchanged**

3. **Save Instance as Blueprint**:
   - User clicks "Save this block as a blueprint" in block options
   - System prompts for blueprint name
   - Checks for name collision with existing blueprints
   - Option to overwrite existing blueprint (with confirmation)
   - **Creates/updates global blueprint, instance remains unchanged**

#### Independence and Decoupling:
- **Delete Blueprint**: Instances continue to exist as custom blocks
- **Edit Instance**: Blueprint and other instances remain unchanged  
- **Delete Instance**: Blueprint and other instances remain unchanged
- **Rename Instance**: Only affects that specific instance

#### Virtual Environment Management (Per Block):
- Each block runs in its own virtual environment managed by `uv`
- Environments are automatically created/updated when:
  - Block is first created
  - Dependencies change in `@atlasvibe` decorator
  - Python version requirements change
- Ensures complete isolation between blocks
- No dependency conflicts between blocks

#### Automatic Metadata Generation:
When a custom block is created or modified:
1. `block_data.json` - Generated from docstring
2. `app.json` - Copied/updated from original
3. `example.md` - Copied/updated from original
4. `manifest` - Regenerated from AST parsing
5. Virtual environment - Created/updated as needed

#### Important Notes:
- **No "empty" blocks**: Every instance starts as a clone of a blueprint
- **No manual file creation**: Everything is done through the UI
- **Real-time updates**: Changes are reflected immediately in the workflow
- **Complete independence**: Blueprints and instances are fully decoupled after creation

## Future Feature: Matrioskas (Nested Workflows)

**Status**: Planned but not yet implemented

### Concept
Matrioskas solve the problem of managing multiple similar blocks without manual synchronization. Instead of editing dozens of similar instances individually, users can group blocks into reusable sub-workflows.

### Features:
- **Group Definition**: Select multiple blocks and their connections to create a Matrioska
- **Input/Output Mapping**: Define inputs and outputs for the entire group
- **Loop/Cron Behavior**: Configure the group to repeat until a condition ("Matrioska Yield") is met
- **Nesting**: Matrioskas can contain other Matrioskas with unlimited depth
- **Instance Management**: Once defined, Matrioskas can be instanced multiple times like blocks

### Examples:
1. **Single Block Matrioska**: Wrap a single XOR block, instance it multiple times in a chain
2. **Complex Workflow Matrioska**: Entire image upscaling workflow becomes a single reusable node
3. **Nested Matrioskas**: Workflows containing other workflows with no nesting limits

### User Experience:
- **Creation**: Select blocks → "Create Matrioska" → Define I/O and behavior
- **Usage**: Drag Matrioska from palette like a regular block
- **Editing**: Double-click Matrioska → Editor shows internal workflow
- **Display**: Appears as single block/node in main workflow

This feature will provide the scalability needed for complex workflows while maintaining AtlasVibe's visual programming paradigm.

### What's NOT Implemented (Visual Feedback)

The following visual feedback features are **missing**:
1. **No border color change** during regeneration
2. **No "regenerating" label** above blocks
3. **No blinking animation**
4. **No isRegenerating state tracking**

To implement visual feedback, you would need:
```typescript
// In block store
interface BlockState {
  isRegenerating: boolean;
  regenerationStartTime?: number;
}

// In default-block.tsx
className={clsx(
  existingClasses,
  { "border-orange-500 animate-pulse": isRegenerating }
)}

// Regenerating label
{isRegenerating && (
  <div className="absolute -top-6 animate-blink">
    Regenerating...
  </div>
)}
```

### Testing Metadata Generation

```python
# Generate block_data.json from docstring
from cli.utils.generate_docstring_json import generate_docstring_json
generate_docstring_json()  # Processes all blocks

# Generate manifest from Python file
from captain.utils.manifest.build_manifest import create_manifest
manifest = create_manifest("/path/to/block.py")

# Test file watching
from captain.services.consumer.blocks_watcher import BlocksWatcher
watcher = BlocksWatcher()
await watcher.run(stop_flag)  # Monitors for changes
```

### Key Functions and Locations

- **Manifest Generation**: `captain/utils/manifest/build_manifest.py`
- **AST Parsing**: `captain/utils/manifest/build_ast.py`
- **Docstring Extraction**: `cli/utils/generate_docstring_json.py`
- **File Watching**: `captain/services/consumer/blocks_watcher.py`
- **WebSocket Manager**: `captain/internal/wsmanager.py`
- **Block Copy/Update**: `captain/utils/project_structure.py`
- **API Endpoints**: `captain/routes/blocks.py`

### Important Notes

1. **Decorator Compatibility**: Both `@atlasvibe` and `@atlasvibe_node` are recognized
2. **Docstring Format**: Must use NumPy-style docstrings (not Google style for blocks)
3. **File Naming**: Python file must match the folder name exactly
4. **__init__.py**: Required in each block directory
5. **Manifest vs Metadata**: Manifest is generated on-the-fly, block_data.json is persisted

