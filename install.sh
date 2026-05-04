#!/usr/bin/env bash
# Mnemonic Memory Plugin - Auto Installer for Hermes
# Usage: curl -sSL https://raw.githubusercontent.com/kopalam/Mnemonic/main/install.sh | bash

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Mnemonic Memory Plugin Installer       ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"

# Detect Hermes profile
HERMES_PROFILE="${HERMES_PROFILE:-$HOME/.hermes/profiles/oper}"
PLUGIN_DIR="$HERMES_PROFILE/plugins/memory/mnemonic"

# Check dependencies
command -v docker >/dev/null 2>&1 || { echo -e "${RED}Error: Docker is required${NC}"; exit 1; }
command -v docker-compose >/dev/null 2>&1 || command -v docker >/dev/null 2>&1 || { echo -e "${RED}Error: docker-compose is required${NC}"; exit 1; }

# Prompt for database configuration
echo -e "\n${YELLOW}Database Configuration:${NC}"
read -p "PostgreSQL Host [localhost]: " DB_HOST
DB_HOST=${DB_HOST:-localhost}

read -p "PostgreSQL Port [5432]: " DB_PORT
DB_PORT=${DB_PORT:-5432}

read -p "Database Name [mnemonic]: " DB_NAME
DB_NAME=${DB_NAME:-mnemonic}

read -p "Database User [postgres]: " DB_USER
DB_USER=${DB_USER:-postgres}

read -sp "Database Password: " DB_PASSWORD
echo

read -p "API Port [8010]: " API_PORT
API_PORT=${API_PORT:-8010}

# Namespace configuration
read -p "Hermes Namespace [hermes:boss:hnoe:*]: " NAMESPACE
NAMESPACE=${NAMESPACE:-hermes:boss:hnoe:*}

# Clone or update repository
INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/share/mnemonic}"
if [ -d "$INSTALL_DIR" ]; then
    echo -e "\n${YELLOW}Updating existing installation...${NC}"
    cd "$INSTALL_DIR" && git pull
else
    echo -e "\n${GREEN}Cloning Mnemonic repository...${NC}"
    git clone https://github.com/kopalam/Mnemonic.git "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# Create .env file
cat > .env << EOF
# Database
DB_HOST=${DB_HOST}
DB_PORT=${DB_PORT}
DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASSWORD}

# API
API_HOST=0.0.0.0
API_PORT=${API_PORT}

# Embedding (SiliconFlow Qwen3-Embedding-0.6B)
EMBEDDING_PROVIDER=siliconflow
EMBEDDING_MODEL=Qwen/Qwen3-Embedding-0.6B
SILICONFLOW_API_KEY=${SILICONFLOW_API_KEY:-}

# Logging
LOG_LEVEL=INFO
EOF

echo -e "${GREEN}✓ Created .env configuration${NC}"

# Test database connection
echo -e "\n${YELLOW}Testing database connection...${NC}"
if command -v psql >/dev/null 2>&1; then
    if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Database connection successful${NC}"
    else
        echo -e "${RED}✗ Cannot connect to database. Please check credentials.${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠ psql not found, skipping connection test${NC}"
fi

# Start Docker containers
echo -e "\n${GREEN}Starting Mnemonic API...${NC}"
docker-compose up -d --build

# Wait for API to be ready
echo -e "${YELLOW}Waiting for API to start...${NC}"
for i in {1..30}; do
    if curl -s "http://localhost:${API_PORT}/health" | grep -q '"status":"ok"'; then
        echo -e "${GREEN}✓ Mnemonic API is running on port ${API_PORT}${NC}"
        break
    fi
    sleep 1
done

# Install Hermes plugin configuration
echo -e "\n${GREEN}Configuring Hermes plugin...${NC}"
mkdir -p "$PLUGIN_DIR"

cat > "$PLUGIN_DIR/config.json" << EOF
{
  "api_url": "http://localhost:${API_PORT}",
  "namespace": "${NAMESPACE}"
}
EOF

# Update Hermes config.yaml if needed
HERMES_CONFIG="$HERMES_PROFILE/config.yaml"
if [ -f "$HERMES_CONFIG" ]; then
    if grep -q "memory:" "$HERMES_CONFIG"; then
        if ! grep -q "provider: mnemonic" "$HERMES_CONFIG"; then
            # Backup and update
            cp "$HERMES_CONFIG" "$HERMES_CONFIG.bak"
            # This is a simple approach - in production, use yq or Python
            echo -e "${YELLOW}Please add 'provider: mnemonic' under memory: in $HERMES_CONFIG${NC}"
        fi
    else
        echo -e "${YELLOW}Please add memory configuration to $HERMES_CONFIG${NC}"
    fi
fi

echo -e "\n${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║        Installation Complete!           ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
echo -e "\nAPI Endpoint: http://localhost:${API_PORT}"
echo -e "Health Check: curl http://localhost:${API_PORT}/health"
echo -e "Plugin Config: $PLUGIN_DIR/config.json"
echo -e "\nTest memory creation:"
echo -e "  curl -X POST http://localhost:${API_PORT}/memories \\"
echo -e "    -H 'Content-Type: application/json' \\"
echo -e "    -H 'X-Namespace: ${NAMESPACE}' \\"
echo -e "    -d '{\"content\": \"Hello Mnemonic!\"}'"