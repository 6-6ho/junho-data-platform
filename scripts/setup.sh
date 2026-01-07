#!/bin/bash
# First-time setup script for the target server (laptop)
# Run this manually on the laptop before the first GitHub Actions deployment

set -e

echo "=== Trade Helper Initial Setup ==="

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed."
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    echo "Error: Docker Compose is not installed."
    exit 1
fi

echo "[OK] Docker is available"

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "Warning: Node.js is not installed. Frontend build may fail."
    echo "Install Node.js: https://nodejs.org/"
fi

# Check npm
if ! command -v npm &> /dev/null; then
    echo "Warning: npm is not installed. Frontend build may fail."
fi

# Check Git
if ! command -v git &> /dev/null; then
    echo "Error: Git is not installed."
    exit 1
fi

echo "[OK] Git is available"

# Build frontend
if [ -d "frontend" ]; then
    echo "Building frontend..."
    cd frontend
    npm install
    npm run build
    cd ..
    echo "[OK] Frontend built"
fi

# Start services
echo "Starting Docker services..."
docker compose up -d --build

echo ""
echo "=== Setup Complete ==="
echo "Access the app at: http://localhost:3000"
