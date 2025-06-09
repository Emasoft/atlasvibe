sync:
  uv run python3 avblock.py sync

add args:
  uv run python3 avblock.py add {{invocation_directory()}}/{{args}}

init:
  just init-docs & just init-blocks

init-docs:
  cd docs && pnpm install

init-blocks:
  uv sync # Replaces poetry install

update:
  just update-docs & just update-blocks

update-docs:
  cd docs && pnpm update

update-blocks:
  uv sync --reinstall # Or `uv pip install --upgrade <packages>` for specific updates

dev:
  cd docs && pnpm dev

build:
  cd docs && pnpm build

format:
  uv run ruff format .

lint:
  uv run ruff check .
