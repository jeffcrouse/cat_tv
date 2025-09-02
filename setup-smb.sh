#!/bin/bash

# SMB Setup Script for Samba File Sharing

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== SMB File Sharing Setup ===${NC}"
echo

# Prompt for configuration
read -p "Enter the name for the shared volume: " SHARE_NAME
read -p "Enter the username for SMB access: " SMB_USER
read -sp "Enter the password for SMB access: " SMB_PASS
echo
read -sp "Confirm the password: " SMB_PASS_CONFIRM
echo

# Validate password match
if [ "$SMB_PASS" != "$SMB_PASS_CONFIRM" ]; then
    echo -e "${RED}Error: Passwords do not match${NC}"
    exit 1
fi

# Install required packages
echo -e "${YELLOW}Installing Samba packages...${NC}"
sudo apt update
sudo apt install -y samba samba-common-bin

# Backup existing config if it exists
if [ -f /etc/samba/smb.conf ]; then
    echo -e "${YELLOW}Backing up existing smb.conf...${NC}"
    sudo cp /etc/samba/smb.conf /etc/samba/smb.conf.backup.$(date +%Y%m%d_%H%M%S)
fi

# Add share configuration to smb.conf
echo -e "${YELLOW}Configuring Samba share...${NC}"
sudo tee -a /etc/samba/smb.conf > /dev/null << EOF

[$SHARE_NAME]
   path = /
   public = no
   writeable = yes
   browseable = yes
   create mask = 0777
   directory mask = 0777
   valid users = $SMB_USER
EOF

# Create system user if it doesn't exist
if ! id "$SMB_USER" &>/dev/null; then
    echo -e "${YELLOW}Creating system user '$SMB_USER'...${NC}"
    sudo useradd -m -s /bin/bash "$SMB_USER"
fi

# Set SMB password
echo -e "${YELLOW}Setting SMB password for user '$SMB_USER'...${NC}"
echo -e "$SMB_PASS\n$SMB_PASS" | sudo smbpasswd -a "$SMB_USER" -s

# Restart Samba service
echo -e "${YELLOW}Restarting Samba service...${NC}"
sudo systemctl restart smbd
sudo systemctl enable smbd

# Display connection information
LOCAL_IP=$(hostname -I | awk '{print $1}')
echo
echo -e "${GREEN}=== SMB Setup Complete ===${NC}"
echo -e "Share name: ${GREEN}$SHARE_NAME${NC}"
echo -e "Username: ${GREEN}$SMB_USER${NC}"
echo -e "Access from Windows: ${GREEN}\\\\$LOCAL_IP\\$SHARE_NAME${NC}"
echo -e "Access from Mac/Linux: ${GREEN}smb://$LOCAL_IP/$SHARE_NAME${NC}"
echo
echo -e "${YELLOW}Note: Make sure your firewall allows SMB traffic (port 445)${NC}"