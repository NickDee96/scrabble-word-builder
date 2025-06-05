#!/bin/bash

# Docker Compose Helper Script for Scrabble Word Builder

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if Docker is running
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    print_success "Docker is running"
}

# Function to check if docker-compose is available
check_docker_compose() {
    if ! command -v docker-compose >/dev/null 2>&1; then
        print_error "docker-compose is not installed. Please install docker-compose and try again."
        exit 1
    fi
    print_success "docker-compose is available"
}

# Function to build and start services
start_services() {
    local env=${1:-production}
    
    print_status "Starting Scrabble Word Builder in $env mode..."
    
    case $env in
        "dev"|"development")
            docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d
            ;;
        "prod"|"production")
            docker-compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
            ;;
        *)
            docker-compose up --build -d
            ;;
    esac
    
    print_success "Services started successfully!"
    print_status "Frontend: http://localhost:3000"
    print_status "Backend API: http://localhost:5000"
    print_status "Backend Health: http://localhost:5000/api/health"
}

# Function to stop services
stop_services() {
    print_status "Stopping Scrabble Word Builder services..."
    docker-compose down
    print_success "Services stopped successfully!"
}

# Function to show logs
show_logs() {
    local service=$1
    if [ -z "$service" ]; then
        docker-compose logs -f
    else
        docker-compose logs -f "$service"
    fi
}

# Function to show service status
show_status() {
    print_status "Service Status:"
    docker-compose ps
    
    print_status "Health Status:"
    docker-compose exec backend curl -f http://localhost:5000/api/health 2>/dev/null || print_warning "Backend health check failed"
    docker-compose exec frontend curl -f http://localhost:3000/ 2>/dev/null || print_warning "Frontend health check failed"
}

# Function to clean up
cleanup() {
    print_status "Cleaning up Docker resources..."
    docker-compose down -v --remove-orphans
    docker system prune -f
    print_success "Cleanup completed!"
}

# Function to rebuild services
rebuild() {
    print_status "Rebuilding services..."
    docker-compose down
    docker-compose build --no-cache
    docker-compose up -d
    print_success "Services rebuilt and started!"
}

# Function to show help
show_help() {
    echo "Docker Helper Script for Scrabble Word Builder"
    echo ""
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  start [env]     Start services (env: dev/development, prod/production)"
    echo "  stop            Stop services"
    echo "  restart [env]   Restart services"
    echo "  logs [service]  Show logs (service: backend, frontend, or all)"
    echo "  status          Show service status and health"
    echo "  rebuild         Rebuild and restart services"
    echo "  cleanup         Stop services and clean up Docker resources"
    echo "  help            Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start dev    # Start in development mode"
    echo "  $0 start prod   # Start in production mode"
    echo "  $0 logs backend # Show backend logs"
    echo "  $0 status       # Check service status"
}

# Main script logic
main() {
    check_docker
    check_docker_compose
    
    case ${1:-help} in
        "start")
            start_services $2
            ;;
        "stop")
            stop_services
            ;;
        "restart")
            stop_services
            start_services $2
            ;;
        "logs")
            show_logs $2
            ;;
        "status")
            show_status
            ;;
        "rebuild")
            rebuild
            ;;
        "cleanup")
            cleanup
            ;;
        "help"|"--help"|"-h")
            show_help
            ;;
        *)
            print_error "Unknown command: $1"
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
