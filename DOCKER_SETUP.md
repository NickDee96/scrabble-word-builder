# Docker Setup for Scrabble Word Builder

This guide explains how to run the Scrabble Word Builder application using Docker and Docker Compose.

## Prerequisites

- Docker Desktop (Windows/Mac) or Docker Engine (Linux)
- Docker Compose v2.0+
- At least 2GB of available RAM
- At least 1GB of available disk space

## Quick Start

### 1. Production Mode (Recommended)

```bash
# Start the application in production mode
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d

# Or using the helper script (Windows)
docker-helper.bat start prod

# Or using the helper script (Linux/Mac)
./docker-helper.sh start prod
```

### 2. Development Mode

```bash
# Start the application in development mode
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d

# Or using the helper script
docker-helper.bat start dev
```

### 3. Basic Mode

```bash
# Start with default configuration
docker-compose up --build -d
```

## Access the Application

- **Frontend (React/Next.js)**: http://localhost:3000
- **Backend API**: http://localhost:5000
- **Health Check**: http://localhost:5000/api/health

## Docker Helper Scripts

We provide helper scripts to simplify Docker operations:

### Windows (`docker-helper.bat`)

```cmd
# Start services
docker-helper.bat start [dev|prod]

# Stop services
docker-helper.bat stop

# View logs
docker-helper.bat logs [backend|frontend]

# Check status
docker-helper.bat status

# Rebuild services
docker-helper.bat rebuild

# Clean up
docker-helper.bat cleanup
```

### Linux/Mac (`docker-helper.sh`)

```bash
# Make script executable
chmod +x docker-helper.sh

# Start services
./docker-helper.sh start [dev|prod]

# Stop services
./docker-helper.sh stop

# View logs
./docker-helper.sh logs [backend|frontend]

# Check status
./docker-helper.sh status

# Rebuild services
./docker-helper.sh rebuild

# Clean up
./docker-helper.sh cleanup
```

## Docker Compose Files

### `docker-compose.yml` (Base Configuration)
- Defines the basic services (frontend and backend)
- Sets up networking between containers
- Configures health checks
- Exposes ports (3000 for frontend, 5000 for backend)

### `docker-compose.prod.yml` (Production Override)
- Enables automatic restarts
- Configures logging with rotation
- Optimized for production workloads

### `docker-compose.dev.yml` (Development Override)
- Enables hot reloading for both frontend and backend
- Mounts source code as volumes for live editing
- Sets development environment variables
- Enables Flask debug mode

## Environment Variables

### Backend (Flask)
- `FLASK_ENV`: Environment mode (development/production)
- `FLASK_DEBUG`: Enable Flask debug mode (1/0)
- `FLASK_APP`: Main application file (app.py)
- `FLASK_RUN_HOST`: Host to bind to (0.0.0.0 for Docker)
- `FLASK_RUN_PORT`: Port to listen on (5000)

### Frontend (Next.js)
- `NODE_ENV`: Environment mode (development/production)
- `NEXT_PUBLIC_API_URL`: Backend API URL
- `PORT`: Port to listen on (3000)
- `HOSTNAME`: Host to bind to (0.0.0.0 for Docker)

## Services Architecture

```
┌─────────────────┐    HTTP     ┌─────────────────┐
│                 │   Requests  │                 │
│   Frontend      │◄───────────►│   Backend       │
│   (Next.js)     │             │   (Flask)       │
│   Port: 3000    │             │   Port: 5000    │
│                 │             │                 │
└─────────────────┘             └─────────────────┘
         │                               │
         │                               │
    ┌────▼────┐                     ┌────▼────┐
    │ Docker  │                     │ Docker  │
    │Container│                     │Container│
    └─────────┘                     └─────────┘
         │                               │
         └───────────────┬───────────────┘
                         │
                ┌────────▼────────┐
                │ Docker Network  │
                │ (scrabble-net)  │
                └─────────────────┘
```

## Health Checks

Both services include built-in health checks:

- **Backend Health**: `GET /api/health`
- **Frontend Health**: `GET /` (homepage)

Health checks run every 30 seconds and help Docker Compose manage service dependencies.

## Volume Mounts

### Production
- Word list file is mounted read-only for easy updates

### Development
- Source code directories are mounted for live editing
- Node modules and build artifacts are preserved in named volumes

## Networking

Services communicate through a custom Docker network (`scrabble-network`):
- **Internal communication**: `http://backend:5000` (frontend to backend)
- **External access**: `http://localhost:3000` and `http://localhost:5000`

## Troubleshooting

### Common Issues

1. **Port already in use**
   ```bash
   # Check what's using the ports
   netstat -ano | findstr :3000
   netstat -ano | findstr :5000
   
   # Stop the process or change ports in docker-compose.yml
   ```

2. **Services not starting**
   ```bash
   # Check service logs
   docker-compose logs backend
   docker-compose logs frontend
   ```

3. **Health checks failing**
   ```bash
   # Check service status
   docker-compose ps
   
   # Test health endpoints manually
   curl http://localhost:5000/api/health
   curl http://localhost:3000
   ```

4. **Frontend can't reach backend**
   - Ensure `NEXT_PUBLIC_API_URL` is set correctly
   - Check Docker network connectivity
   - Verify backend is healthy

### Debugging Commands

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Execute commands inside containers
docker-compose exec backend bash
docker-compose exec frontend sh

# Check container status
docker-compose ps

# Check Docker networks
docker network ls
docker network inspect scrabble_scrabble-network
```

## Performance Optimization

### Production Optimizations
- Multi-stage Docker builds reduce image size
- Health checks ensure service reliability
- Log rotation prevents disk space issues
- Automatic restarts handle temporary failures

### Development Optimizations
- Volume mounts enable hot reloading
- Debug mode provides detailed error information
- Source maps are enabled for better debugging

## Security Considerations

- Services run with non-root users where possible
- Internal network isolates services from external access
- Only necessary ports are exposed
- Environment variables manage sensitive configuration

## Backup and Updates

### Updating the Word List
1. Replace `Collins Scrabble Words (2019).txt` in the project root
2. Restart the backend service:
   ```bash
   docker-compose restart backend
   ```

### Application Updates
1. Pull latest code changes
2. Rebuild and restart services:
   ```bash
   docker-compose down
   docker-compose up --build -d
   ```

## Monitoring

### Service Status
```bash
# Check if services are running
docker-compose ps

# Check service health
curl -f http://localhost:5000/api/health
curl -f http://localhost:3000/
```

### Resource Usage
```bash
# Check resource usage
docker stats

# Check disk usage
docker system df
```

### Logs
```bash
# Follow logs in real-time
docker-compose logs -f

# View last 100 lines
docker-compose logs --tail=100
```

This Docker setup provides a robust, scalable, and maintainable deployment solution for the Scrabble Word Builder application.
