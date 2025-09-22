#!/bin/bash

# PriceScan Deployment Script
# Usage: ./deploy.sh [dev|prod]

set -e

ENVIRONMENT=${1:-dev}

echo "🚀 Deploying PriceScan in $ENVIRONMENT mode..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please create it from .env.example"
    exit 1
fi

# Build images
echo "🔨 Building Docker images..."
docker-compose build

# Stop existing containers
echo "🛑 Stopping existing containers..."
docker-compose down

# Start services
if [ "$ENVIRONMENT" = "prod" ]; then
    echo "🏭 Starting production services..."
    docker-compose -f docker-compose.prod.yml up -d
else
    echo "🛠️ Starting development services..."
    docker-compose up -d
fi

# Wait for database
echo "⏳ Waiting for database to be ready..."
sleep 10

# Run migrations
echo "📊 Running database migrations..."
docker-compose exec web_pricescan python manage.py migrate

# Create superuser (only in dev)
if [ "$ENVIRONMENT" = "dev" ]; then
    echo "👤 Creating superuser..."
    docker-compose exec web_pricescan python manage.py createsuperuser --noinput || true
fi

# Collect static files
echo "📁 Collecting static files..."
docker-compose exec web_pricescan python manage.py collectstatic --noinput

# Load initial data
echo "📦 Loading initial data..."
docker-compose exec web_pricescan python manage.py loaddata fixtures/initial_data.json || true

# Start monitoring (if enabled)
if [ "$ENVIRONMENT" = "prod" ] && [ "$PROMETHEUS_ENABLED" = "true" ]; then
    echo "📊 Starting monitoring services..."
    docker-compose --profile monitoring up -d
fi

echo "✅ Deployment completed successfully!"
echo ""
echo "🌐 Services available at:"
echo "   - API: http://localhost:9040/api/"
echo "   - Swagger: http://localhost:9040/api/docs/"
echo "   - Admin: http://localhost:9040/admin/"
echo ""

if [ "$ENVIRONMENT" = "prod" ] && [ "$PROMETHEUS_ENABLED" = "true" ]; then
    echo "📊 Monitoring:"
    echo "   - Prometheus: http://localhost:9090"
    echo "   - Grafana: http://localhost:3000"
    echo ""
fi

echo "🔍 Check logs with: docker-compose logs -f"
echo "🛑 Stop services with: docker-compose down"

