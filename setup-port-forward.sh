#!/bin/bash

# Forward port 80 to 8080 on Raspberry Pi (persistent)

set -e

if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

echo "Setting up port forwarding from 80 to 8080..."

# Install iptables if not present
if ! command -v iptables &> /dev/null; then
    echo "Installing iptables..."
    apt-get update
    apt-get install -y iptables
fi

# Add iptables rules
iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 8080
iptables -t nat -A OUTPUT -p tcp --dport 80 -o lo -j REDIRECT --to-port 8080

# Install iptables-persistent if needed
if ! dpkg -l | grep -q iptables-persistent; then
    echo "Installing iptables-persistent..."
    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y iptables-persistent
fi

# Save rules
echo "Saving iptables rules..."
iptables-save > /etc/iptables/rules.v4

echo "Done! Port 80 now forwards to 8080 (persists after reboot)"
echo ""
echo "To remove later:"
echo "  sudo iptables -t nat -D PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 8080"
echo "  sudo iptables -t nat -D OUTPUT -p tcp --dport 80 -o lo -j REDIRECT --to-port 8080"
echo "  sudo iptables-save > /etc/iptables/rules.v4"