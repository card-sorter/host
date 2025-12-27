#!/bin/bash

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting installation...${NC}"

# Get the absolute path of the project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${PROJECT_DIR}/venv"

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 is not installed. Please install it first.${NC}"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv "$VENV_DIR"
else
    echo -e "${YELLOW}Virtual environment already exists.${NC}"
fi

# Activate virtual environment and install requirements
echo -e "${YELLOW}Installing requirements...${NC}"
source "${VENV_DIR}/bin/activate"
pip install --upgrade pip
pip install -r "${PROJECT_DIR}/requirements.txt"
deactivate

# Copy service file to systemd directory
echo -e "${YELLOW}Installing systemd service...${NC}"
sudo cp csr-host.service /etc/systemd/system/

# Replace placeholder paths in the service file
sudo sed -i "s|PROJECT_DIR|${PROJECT_DIR}|g" /etc/systemd/system/csr-host.service

# Reload systemd, enable and start service
sudo systemctl daemon-reload
sudo systemctl enable csr-host.service
sudo systemctl start csr-host.service

echo -e "${GREEN}Installation complete!${NC}"
echo -e "${GREEN}Service installed and started!${NC}"
echo ""
echo "Useful commands:"
echo "  Check status: sudo systemctl status csr-host.service"
echo "  View logs:    sudo journalctl -u csr-host.service -f"
echo "  Restart:      sudo systemctl restart csr-host.service"