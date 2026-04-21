#!/bin/bash
# ==============================================================================
# QUANTNUIS EC2 API - INITIAL SETUP SCRIPT
# ==============================================================================
# Run this script once on a fresh Ubuntu 22.04 EC2 instance
# Usage: sudo bash setup.sh
# ==============================================================================

set -e

echo "=========================================="
echo "Quantnuis EC2 API - Initial Setup"
echo "=========================================="

# Update system
echo "[1/8] Updating system packages..."
apt-get update && apt-get upgrade -y

# Install required packages
echo "[2/8] Installing required packages..."
apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    python3-pip \
    postgresql \
    postgresql-contrib \
    nginx \
    certbot \
    python3-certbot-nginx \
    git \
    curl \
    libsndfile1 \
    ffmpeg

# Create application user
echo "[3/8] Creating application user..."
useradd -m -s /bin/bash quantnuis || echo "User already exists"

# Create application directory
echo "[4/8] Creating application directory..."
mkdir -p /opt/quantnuis
chown quantnuis:quantnuis /opt/quantnuis

# Setup PostgreSQL
echo "[5/8] Setting up PostgreSQL..."
sudo -u postgres psql -c "CREATE USER quantnuis WITH PASSWORD 'CHANGE_ME_IN_PRODUCTION';" || echo "User might already exist"
sudo -u postgres psql -c "CREATE DATABASE quantnuis OWNER quantnuis;" || echo "Database might already exist"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE quantnuis TO quantnuis;"

# Create virtual environment
echo "[6/8] Creating Python virtual environment..."
sudo -u quantnuis python3.11 -m venv /opt/quantnuis/venv

# Setup systemd service
echo "[7/8] Setting up systemd service..."
cp /opt/quantnuis/deployment/ec2/quantnuis-api.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable quantnuis-api

# Setup nginx (basic config, SSL will be added with certbot)
echo "[8/8] Setting up Nginx..."
cp /opt/quantnuis/deployment/ec2/nginx.conf /etc/nginx/sites-available/quantnuis
ln -sf /etc/nginx/sites-available/quantnuis /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

echo "=========================================="
echo "Initial setup complete!"
echo ""
echo "Next steps:"
echo "1. Update the PostgreSQL password in /opt/quantnuis/.env"
echo "2. Run: sudo -u postgres psql -c \"ALTER USER quantnuis WITH PASSWORD 'your_secure_password';\""
echo "3. Configure your domain DNS to point to this server"
echo "4. Run: sudo certbot --nginx -d your-domain.com"
echo "5. Run: sudo bash deploy.sh"
echo "=========================================="
