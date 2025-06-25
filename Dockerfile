# Multi-stage Dockerfile for AtlasVibe
# Stage 1: Build environment
FROM node:20-slim AS builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for Python package management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:${PATH}"

# Set working directory
WORKDIR /app

# Copy package files
COPY package.json pnpm-lock.yaml ./
COPY pyproject.toml uv.lock ./

# Install pnpm
RUN npm install -g pnpm@9

# Install Node dependencies
RUN pnpm install --frozen-lockfile

# Install Python dependencies
RUN uv venv && \
    . .venv/bin/activate && \
    uv sync --frozen

# Copy source code
COPY . .

# Build the application
RUN pnpm run build

# Stage 2: Test environment with Playwright
FROM mcr.microsoft.com/playwright:v1.40.0-focal AS test

# Install all required dependencies for headless Electron
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
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

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:${PATH}"

# Install pnpm
RUN npm install -g pnpm@9

WORKDIR /app

# Copy from builder
COPY --from=builder /app /app

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

# Copy test entrypoint
COPY docker/entrypoint-test.sh /app/
RUN chmod +x /app/entrypoint-test.sh

# Copy test runner
COPY run_tests_docker.py /app/

# Use entrypoint for proper headless setup
ENTRYPOINT ["/app/entrypoint-test.sh"]

# Stage 3: Runtime environment
FROM node:20-slim AS runtime

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
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
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:${PATH}"

WORKDIR /app

# Copy built application
COPY --from=builder /app /app

# Set up virtual display
ENV DISPLAY=:99

# Expose ports
EXPOSE 5173 11060

# Default command
CMD ["sh", "-c", "Xvfb :99 -screen 0 1024x768x24 > /dev/null 2>&1 & pnpm run start-project"]
