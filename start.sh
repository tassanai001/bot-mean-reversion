#!/bin/bash

###############################################################################
# Trading Bot Docker Management Script
# This script provides a CLI interface to manage the trading bot container
###############################################################################

# Color codes for better UX
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Service name from docker-compose.yml
SERVICE_NAME="trading-bot"
CONTAINER_NAME="mean-reversion-bot"

###############################################################################
# Helper Functions
###############################################################################

# Print colored messages
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

print_header() {
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
}

# Check if .env file exists
check_env_file() {
    if [ ! -f ".env" ]; then
        print_warning ".env file not found!"
        print_info "Please create a .env file with your API keys and configuration."
        print_info "You can use .env.example as a template if available."
        exit 1
    fi
}

###############################################################################
# Command Functions
###############################################################################

# Build the Docker image
build_image() {
    print_header "Building Docker Image"
    check_docker
    check_env_file

    print_info "Building image for $SERVICE_NAME..."
    if docker-compose build --no-cache; then
        print_success "Image built successfully!"
    else
        print_error "Failed to build image."
        exit 1
    fi
}

# Start the container
start_container() {
    print_header "Starting Trading Bot"
    check_docker
    check_env_file

    # Check if container is already running
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        print_warning "Container is already running!"
        print_info "Use './start.sh status' to check status or './start.sh restart' to restart."
        exit 0
    fi

    print_info "Starting $SERVICE_NAME in detached mode..."
    if docker-compose up -d; then
        print_success "Container started successfully!"
        print_info "Use './start.sh logs' to view real-time logs."
        print_info "Use './start.sh status' to check container status."
    else
        print_error "Failed to start container."
        exit 1
    fi
}

# Stop the container
stop_container() {
    print_header "Stopping Trading Bot"
    check_docker

    # Check if container is running
    if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        print_warning "Container is not running."
        exit 0
    fi

    print_info "Stopping and removing $SERVICE_NAME..."
    if docker-compose down; then
        print_success "Container stopped and removed successfully!"
    else
        print_error "Failed to stop container."
        exit 1
    fi
}

# Restart the container
restart_container() {
    print_header "Restarting Trading Bot"
    check_docker

    print_info "Restarting $SERVICE_NAME..."
    if docker-compose restart; then
        print_success "Container restarted successfully!"
        print_info "Use './start.sh logs' to view real-time logs."
    else
        print_error "Failed to restart container."
        exit 1
    fi
}

# View container logs
view_logs() {
    print_header "Trading Bot Logs"
    check_docker

    # Check if container exists
    if ! docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        print_error "Container does not exist. Please start it first."
        exit 1
    fi

    print_info "Following logs for $SERVICE_NAME (Ctrl+C to exit)..."
    echo ""
    docker-compose logs -f --tail=100
}

# Show container status
show_status() {
    print_header "Trading Bot Status"
    check_docker

    # Check if container exists
    if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        # Get container status
        STATUS=$(docker inspect -f '{{.State.Status}}' "$CONTAINER_NAME" 2>/dev/null)
        RUNNING=$(docker inspect -f '{{.State.Running}}' "$CONTAINER_NAME" 2>/dev/null)
        STARTED=$(docker inspect -f '{{.State.StartedAt}}' "$CONTAINER_NAME" 2>/dev/null)

        echo ""
        echo -e "${CYAN}Container Name:${NC} $CONTAINER_NAME"

        if [ "$RUNNING" = "true" ]; then
            echo -e "${CYAN}Status:${NC} ${GREEN}Running ✓${NC}"
        else
            echo -e "${CYAN}Status:${NC} ${RED}Stopped ✗${NC}"
        fi

        echo -e "${CYAN}State:${NC} $STATUS"
        echo -e "${CYAN}Started At:${NC} $STARTED"

        # Show resource usage if running
        if [ "$RUNNING" = "true" ]; then
            echo ""
            print_info "Resource Usage:"
            docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" "$CONTAINER_NAME"
        fi

        echo ""
        print_info "Logs directory: ./logs"

        # Check if logs directory has files
        if [ -d "./logs" ] && [ "$(ls -A ./logs)" ]; then
            LOG_COUNT=$(ls -1 ./logs | wc -l | tr -d ' ')
            print_info "Log files found: $LOG_COUNT"
        else
            print_warning "No log files found yet."
        fi
    else
        print_warning "Container does not exist."
        print_info "Use './start.sh build' to build the image."
        print_info "Use './start.sh start' to start the container."
    fi
    echo ""
}

# Show help/usage
show_help() {
    print_header "Trading Bot Management Script"
    echo ""
    echo -e "${CYAN}Usage:${NC}"
    echo -e "  ./start.sh ${GREEN}<command>${NC}"
    echo ""
    echo -e "${CYAN}Available Commands:${NC}"
    echo -e "  ${GREEN}build${NC}       Build or rebuild the Docker image"
    echo -e "  ${GREEN}start${NC}       Start the container in detached mode"
    echo -e "  ${GREEN}up${NC}          Alias for 'start'"
    echo -e "  ${GREEN}stop${NC}        Stop and remove the container"
    echo -e "  ${GREEN}restart${NC}     Restart the container"
    echo -e "  ${GREEN}logs${NC}        Follow real-time logs (Ctrl+C to exit)"
    echo -e "  ${GREEN}status${NC}      Show container status and resource usage"
    echo -e "  ${GREEN}help${NC}        Show this help message"
    echo ""
    echo -e "${CYAN}Examples:${NC}"
    echo -e "  ./start.sh build       # Build the Docker image"
    echo -e "  ./start.sh start       # Start the trading bot"
    echo -e "  ./start.sh logs        # View live logs"
    echo -e "  ./start.sh status      # Check if bot is running"
    echo -e "  ./start.sh restart     # Restart the bot"
    echo -e "  ./start.sh stop        # Stop the bot"
    echo ""
}

###############################################################################
# Main Script Logic
###############################################################################

# Make script executable (if not already)
if [ ! -x "$0" ]; then
    chmod +x "$0"
    print_success "Script is now executable!"
fi

# Check if command is provided
if [ $# -eq 0 ]; then
    print_error "No command provided."
    echo ""
    show_help
    exit 1
fi

# Parse command
COMMAND=$1

case $COMMAND in
    build)
        build_image
        ;;
    start|up)
        start_container
        ;;
    stop)
        stop_container
        ;;
    restart)
        restart_container
        ;;
    logs)
        view_logs
        ;;
    status)
        show_status
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $COMMAND"
        echo ""
        show_help
        exit 1
        ;;
esac

exit 0