#!/bin/bash
# ==============================================================================
# QUANTNUIS EC2 API - DEPLOYMENT SCRIPT
# ==============================================================================
# Run this script to deploy or update the application
# Usage: sudo bash deploy.sh [--skip-deps]
# ==============================================================================

set -e

APP_DIR="/opt/quantnuis"
REPO_URL="https://github.com/YOUR_USERNAME/Quantnuis.git"
BRANCH="main"

echo "=========================================="
echo "Quantnuis EC2 API - Deployment"
echo "=========================================="

# Parse arguments
SKIP_DEPS=false
if [[ "$1" == "--skip-deps" ]]; then
    SKIP_DEPS=true
fi

# Navigate to app directory
cd $APP_DIR

# Pull latest code (or clone if first deploy)
echo "[1/5] Pulling latest code..."
if [ -d ".git" ]; then
    sudo -u quantnuis git fetch origin
    sudo -u quantnuis git reset --hard origin/$BRANCH
else
    # First deployment - clone the repo
    cd /opt
    rm -rf quantnuis
    sudo -u quantnuis git clone -b $BRANCH $REPO_URL quantnuis
    cd quantnuis
fi

# Copy backend files to app directory
echo "[2/5] Setting up backend..."
if [ -d "Quantnuis-Backend" ]; then
    # Copy only backend files
    cp -r Quantnuis-Backend/* $APP_DIR/ 2>/dev/null || true
fi

# Install/update dependencies
if [ "$SKIP_DEPS" = false ]; then
    echo "[3/5] Installing Python dependencies..."
    sudo -u quantnuis $APP_DIR/venv/bin/pip install --upgrade pip
    sudo -u quantnuis $APP_DIR/venv/bin/pip install -r $APP_DIR/requirements-ec2.txt
else
    echo "[3/5] Skipping dependency installation (--skip-deps)"
fi

# Check .env file exists
if [ ! -f "$APP_DIR/.env" ]; then
    echo "[4/5] Creating .env file from template..."
    cp $APP_DIR/deployment/ec2/.env.template $APP_DIR/.env
    chown quantnuis:quantnuis $APP_DIR/.env
    chmod 600 $APP_DIR/.env
    echo "WARNING: Please edit $APP_DIR/.env with your configuration!"
else
    echo "[4/5] .env file already exists"
fi

# Restart service
echo "[5/5] Restarting service..."
systemctl restart quantnuis-api

# Wait and check status
sleep 3
if systemctl is-active --quiet quantnuis-api; then
    echo "=========================================="
    echo "Deployment successful!"
    echo ""
    echo "Service status:"
    systemctl status quantnuis-api --no-pager
    echo ""
    echo "Health check:"
    curl -s http://localhost:8000/health | python3 -m json.tool || echo "Health check failed"
    echo "=========================================="
else
    echo "=========================================="
    echo "Deployment FAILED - Service not running"
    echo ""
    echo "Check logs with: journalctl -u quantnuis-api -f"
    echo "=========================================="
    exit 1
fi
