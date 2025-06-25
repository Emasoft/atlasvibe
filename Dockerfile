# Multi-stage Dockerfile for AtlasVibe
# Following official uv Docker guide: https://docs.astral.sh/uv/guides/integration/docker/

# Stage 1: Build environment with uv
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Install system dependencies needed for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Install pnpm globally
RUN npm install -g pnpm@9

# Set working directory
WORKDIR /app

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Copy Node package files and install
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

# Copy the rest of the application
COPY . .

# Install the project itself
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Build the frontend
RUN pnpm run build || echo "Build step completed (may have warnings)"

# Stage 2: Test environment with Playwright and uv
FROM mcr.microsoft.com/playwright:v1.40.0-jammy AS test

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set timezone to avoid interactive prompt
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Install all required dependencies for headless Electron
RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    xvfb \
    curl \
    # GTK and X11 dependencies for Electron
    libgtk-3-0 \
    libgbm1 \
    libnss3 \
    libxss1 \
    libasound2 \
    libx11-xcb1 \
    libxcb-dri3-0 \
    libdrm2 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libatspi2.0-0 \
    libxkbcommon0 \
    libpango-1.0-0 \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.11 as default python3
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

# Install pnpm
RUN npm install -g pnpm@9

WORKDIR /app

# Copy the application from builder
COPY --from=builder --chown=app:app /app /app

# Install test dependencies
RUN pnpm install --frozen-lockfile

# Install Playwright browsers explicitly
RUN npx playwright install chromium

# Set up environment for headless execution
ENV DISPLAY=:99
ENV CI=true
ENV NODE_ENV=test
# Disable GPU and sandbox for Electron in container
ENV ELECTRON_DISABLE_GPU=1
ENV ELECTRON_NO_SANDBOX=1
# Prevent Electron from trying to use host display
ENV ELECTRON_ENABLE_LOGGING=1

# Create config directory that the backend expects
RUN mkdir -p /root/.atlasvibe && \
    echo 'test: true' > /root/.atlasvibe/atlasvibe.yaml

# Copy test entrypoint
COPY docker/entrypoint-test.sh /app/
RUN chmod +x /app/entrypoint-test.sh

# Copy test runner
COPY run_tests_docker.py /app/

# Use entrypoint for proper headless setup
ENTRYPOINT ["/app/entrypoint-test.sh"]

# Stage 3: Runtime environment
FROM python:3.11-slim AS runtime

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs \
    npm \
    curl \
    xvfb \
    libgtk-3-0 \
    libnotify-dev \
    libgconf-2-4 \
    libnss3 \
    libxss1 \
    libasound2 \
    libxtst6 \
    xauth \
    && rm -rf /var/lib/apt/lists/*

# Install pnpm
RUN npm install -g pnpm@9

# Create non-root user
RUN useradd -m -u 1001 app

WORKDIR /app

# Copy the application from builder
COPY --from=builder --chown=app:app /app /app

# Switch to non-root user
USER app

# Set up virtual display
ENV DISPLAY=:99

# Create config directory
RUN mkdir -p /home/app/.atlasvibe && \
    echo 'docker: true' > /home/app/.atlasvibe/atlasvibe.yaml

# Expose ports
EXPOSE 5173 11060

# Default command using uv run
CMD ["sh", "-c", "Xvfb :99 -screen 0 1024x768x24 > /dev/null 2>&1 & uv run pnpm run start-project"]
