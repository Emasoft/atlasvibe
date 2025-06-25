#!/bin/bash
# Script to run AtlasVibe tests in Docker

echo "🐳 AtlasVibe Docker Test Runner"
echo "================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed. Please install Docker Compose first.${NC}"
    exit 1
fi

# Determine docker-compose command
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

echo -e "${YELLOW}🔧 Building Docker images...${NC}"
$DOCKER_COMPOSE build atlasvibe-test

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to build Docker images${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker images built successfully${NC}"
echo ""

# Create directories for test results
mkdir -p test-results playwright-report

echo -e "${YELLOW}🧪 Running tests in Docker container...${NC}"
echo ""

# Run tests with proper isolation to prevent display connection
# Unset DISPLAY to ensure container doesn't try to connect to host display
unset DISPLAY

$DOCKER_COMPOSE run \
    --rm \
    --no-deps \
    -e DISPLAY=:99 \
    -e ELECTRON_DISABLE_GPU=1 \
    -e ELECTRON_NO_SANDBOX=1 \
    -e XVFB_SCREEN_SIZE=1280x1024x24 \
    atlasvibe-test

TEST_EXIT_CODE=$?

echo ""
echo -e "${YELLOW}📋 Copying test results...${NC}"

# The results should already be in the mounted volumes
if [ -f "test-results/results.json" ]; then
    echo -e "${GREEN}✅ Test results copied successfully${NC}"
else
    echo -e "${YELLOW}⚠️  No test results file found${NC}"
fi

# Check if HTML report exists
if [ -d "playwright-report" ] && [ "$(ls -A playwright-report)" ]; then
    echo -e "${GREEN}✅ HTML report available in playwright-report/index.html${NC}"
fi

# Cleanup
echo ""
echo -e "${YELLOW}🧹 Cleaning up...${NC}"
$DOCKER_COMPOSE down

echo ""
echo "================================"
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ All tests completed successfully!${NC}"
else
    echo -e "${RED}❌ Some tests failed. Check the results above.${NC}"
fi
echo "================================"

exit $TEST_EXIT_CODE
