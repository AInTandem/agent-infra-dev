#!/bin/bash
# Docker Build and Test Script for AInTandem Agent MCP Scheduler

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
IMAGE_NAME="aintandem-agent-scheduler"
IMAGE_TAG="latest"
CONTAINER_NAME="aintandem-agent-test"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}AInTandem Agent MCP Scheduler - Docker Build${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker daemon is not running${NC}"
    echo "Please start Docker and try again"
    exit 1
fi

echo -e "${GREEN}✓ Docker is running${NC}"
echo ""

# Step 1: Build image
echo -e "${YELLOW}Step 1: Building Docker image...${NC}"
docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Image built successfully${NC}"
else
    echo -e "${RED}✗ Image build failed${NC}"
    exit 1
fi
echo ""

# Step 2: Show image info
echo -e "${YELLOW}Step 2: Image information${NC}"
docker images ${IMAGE_NAME}:${IMAGE_TAG}
echo ""

# Step 3: Run container in test mode
echo -e "${YELLOW}Step 3: Running container in test mode...${NC}"
echo -e "${YELLOW}(Press Ctrl+C to stop)${NC}"
echo ""

docker run --rm \
    --name ${CONTAINER_NAME} \
    -p 8000:8000 \
    -p 7860:7860 \
    -e LOG_LEVEL=INFO \
    -e OPENAI_API_KEY=${OPENAI_API_KEY:-"test_key"} \
    -v $(pwd)/config:/app/config:ro \
    -v aintandem-test-storage:/app/storage \
    ${IMAGE_NAME}:${IMAGE_TAG}

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Docker Test Complete${NC}"
echo -e "${GREEN}========================================${NC}"
