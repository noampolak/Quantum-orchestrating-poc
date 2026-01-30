#!/bin/bash
# Cleanup script for Docker resources related to this project

set -e

echo "🧹 Cleaning up Docker resources for quantum-orchestrating-poc..."

# Stop and remove all containers and volumes
echo "📦 Stopping and removing containers..."
docker-compose down -v --remove-orphans 2>/dev/null || true
docker-compose --profile test down -v --remove-orphans 2>/dev/null || true

# Remove containers by name pattern
echo "🗑️  Removing containers..."
docker ps -a --filter "name=quantum" --format "{{.ID}}" | xargs -r docker rm -f 2>/dev/null || true
docker ps -a --filter "name=temporal" --format "{{.ID}}" | xargs -r docker rm -f 2>/dev/null || true
docker ps -a --filter "name=ensure-temporal" --format "{{.ID}}" | xargs -r docker rm -f 2>/dev/null || true

# Remove images by name pattern
echo "🖼️  Removing images..."
docker images --filter "reference=*quantum-orchestrating-poc*" --format "{{.ID}}" | xargs -r docker rmi -f 2>/dev/null || true

# Remove volumes
echo "💾 Removing volumes..."
docker volume ls --filter "name=quantum" --format "{{.Name}}" | xargs -r docker volume rm 2>/dev/null || true
docker volume ls --filter "name=postgres_data" --format "{{.Name}}" | xargs -r docker volume rm 2>/dev/null || true
docker volume ls --filter "name=quantum-orchestrating-poc" --format "{{.Name}}" | xargs -r docker volume rm 2>/dev/null || true

# Clean build cache
echo "🧼 Cleaning build cache..."
docker builder prune -f

# Remove any orphaned networks
echo "🌐 Cleaning networks..."
docker network prune -f

echo "✅ Cleanup complete!"
echo ""
echo "You can now run: docker-compose up --build"
