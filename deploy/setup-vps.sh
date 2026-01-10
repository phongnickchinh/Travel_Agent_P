#!/bin/bash
# ========================================
# VPS Initial Setup Script
# Travel Agent P - One-time VPS configuration
# ========================================
# Run this script on your VPS after first login:
# curl -fsSL https://raw.githubusercontent.com/phongnickchinh/Travel_Agent_P/main/deploy/setup-vps.sh | bash
# ========================================

set -e

echo "========================================"
echo "🚀 Travel Agent P - VPS Setup"
echo "========================================"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Please run as root (use sudo)"
    exit 1
fi

# Update system
echo "📦 Updating system packages..."
apt-get update
apt-get upgrade -y

# Install dependencies
echo "📦 Installing required packages..."
apt-get install -y \
    curl \
    git \
    ufw \
    certbot \
    python3-certbot-nginx \
    postgresql-client \
    mongodb-clients \
    redis-tools

# Install Docker
echo "🐳 Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    echo "✅ Docker installed"
else
    echo "✅ Docker already installed"
fi

# Install Docker Compose
echo "🐳 Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE_VERSION="2.23.0"
    curl -L "https://github.com/docker/compose/releases/download/v${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" \
        -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    echo "✅ Docker Compose installed"
else
    echo "✅ Docker Compose already installed"
fi

# Configure firewall
echo "🔥 Configuring firewall..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp  # SSH
ufw allow 80/tcp  # HTTP
ufw allow 443/tcp # HTTPS
ufw --force enable
echo "✅ Firewall configured"

# Create deployment directory
echo "📁 Creating deployment directory..."
DEPLOY_PATH="/opt/travel-agent-p"
mkdir -p $DEPLOY_PATH
cd $DEPLOY_PATH

# Clone repository
echo "📥 Cloning repository..."
if [ -d ".git" ]; then
    echo "✅ Repository already cloned, pulling latest..."
    git pull origin main
else
    git clone https://github.com/phongnickchinh/Travel_Agent_P.git .
    echo "✅ Repository cloned"
fi

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p server/logs
mkdir -p server/secrets
mkdir -p server/nginx/ssl
mkdir -p server/nginx/logs
mkdir -p backups
chmod 755 server/logs server/nginx/logs backups

# Create .env file template
echo "📝 Creating .env file..."
if [ ! -f server/.env ]; then
    cp server/.env.production.example server/.env
    echo "⚠️  IMPORTANT: Edit server/.env with your production secrets!"
    echo "   Run: nano $DEPLOY_PATH/server/.env"
else
    echo "✅ .env file already exists"
fi

# Setup SSL certificates (Let's Encrypt)
echo "🔒 Setting up SSL certificates..."
read -p "Enter your domain name (e.g., api.travelagentp.com): " DOMAIN_NAME

if [ ! -z "$DOMAIN_NAME" ]; then
    echo "📝 Generating SSL certificate for $DOMAIN_NAME..."
    
    # Stop nginx if running
    docker-compose down nginx 2>/dev/null || true
    
    # Get certificate
    certbot certonly --standalone \
        --non-interactive \
        --agree-tos \
        --email admin@$DOMAIN_NAME \
        -d $DOMAIN_NAME
    
    # Copy certificates to nginx directory
    cp /etc/letsencrypt/live/$DOMAIN_NAME/fullchain.pem server/nginx/ssl/
    cp /etc/letsencrypt/live/$DOMAIN_NAME/privkey.pem server/nginx/ssl/
    
    # Update nginx config with domain
    sed -i "s/api.travelagentp.com/$DOMAIN_NAME/g" server/nginx/nginx.conf
    
    echo "✅ SSL certificate installed"
    
    # Setup auto-renewal
    echo "📅 Setting up SSL certificate auto-renewal..."
    (crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet && cp /etc/letsencrypt/live/$DOMAIN_NAME/*.pem $DEPLOY_PATH/server/nginx/ssl/ && cd $DEPLOY_PATH && docker-compose restart nginx") | crontab -
    echo "✅ Auto-renewal configured (runs daily at 3 AM)"
else
    echo "⚠️  Skipping SSL setup. You can run certbot manually later."
    echo "⚠️  Using self-signed certificate for testing..."
    
    # Generate self-signed certificate for testing
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout server/nginx/ssl/privkey.pem \
        -out server/nginx/ssl/fullchain.pem \
        -subj "/CN=localhost"
    
    echo "✅ Self-signed certificate created (TESTING ONLY)"
fi

# Setup GitHub SSH key (for git pull in deployment)
echo "🔑 Setting up GitHub deployment key..."
if [ ! -f ~/.ssh/id_ed25519 ]; then
    ssh-keygen -t ed25519 -C "deploy@vps" -f ~/.ssh/id_ed25519 -N ""
    echo "✅ SSH key generated"
    echo "📋 Add this public key to GitHub (Settings > Deploy keys):"
    cat ~/.ssh/id_ed25519.pub
    echo ""
    read -p "Press Enter after adding the key to GitHub..."
else
    echo "✅ SSH key already exists"
fi

# Test GitHub connection
echo "🔗 Testing GitHub connection..."
ssh-keyscan github.com >> ~/.ssh/known_hosts
ssh -T git@github.com || echo "⚠️  Note: 'Permission denied' is normal if using HTTPS clone"

# Create backup script
echo "💾 Creating backup script..."
cat > /usr/local/bin/backup-travelagent.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/travel-agent-p/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Load environment variables
source /opt/travel-agent-p/server/.env

# Backup PostgreSQL
docker-compose -f /opt/travel-agent-p/server/docker-compose.production.yml exec -T postgres \
    pg_dump -U ${POSTGRES_USERNAME:-postgres} ${POSTGRES_DBNAME:-travel_agent_db} > $BACKUP_DIR/postgres_$DATE.sql

# MongoDB Atlas backup (manual via Atlas dashboard)
    # No local MongoDB backup needed

# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.archive" -mtime +7 -delete

echo "✅ Backup completed: $DATE"
EOF

chmod +x /usr/local/bin/backup-travelagent.sh

# Schedule daily backups (2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/backup-travelagent.sh") | crontab -
echo "✅ Daily backup scheduled (2 AM)"

# Pull Docker images
echo "🐳 Pulling Docker images..."
cd server
docker-compose -f docker-compose.production.yml pull

# Show next steps
echo ""
echo "========================================"
echo "✅ VPS Setup Complete!"
echo "========================================"
echo ""
echo "📋 Next Steps:"
echo ""
echo "1. Configure environment variables:"
echo "   nano $DEPLOY_PATH/server/.env"
echo ""
echo "2. Add Firebase credentials:"
echo "   Upload serviceAccount.json to $DEPLOY_PATH/server/secrets/"
echo ""
echo "3. Build and start services:"
echo "   cd $DEPLOY_PATH/server"
echo "   docker-compose -f docker-compose.production.yml up -d --build"
echo ""
echo "4. Check logs:"
echo "   docker-compose -f docker-compose.production.yml logs -f"
echo ""
echo "5. Verify health:"
echo "   curl http://localhost/health"
echo ""
echo "6. Configure DNS:"
echo "   Point your domain to this server's IP: $(curl -s ifconfig.me)"
echo ""
echo "========================================"
echo "📚 Documentation: docs/DEPLOYMENT.md"
echo "🐛 Issues: https://github.com/phongnickchinh/Travel_Agent_P/issues"
echo "========================================"
