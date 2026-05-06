#!/bin/bash
# DroneResearch Pi 1 installer
# Run as: bash pi/install.sh

set -e

echo "=== DroneResearch Pi installer ==="

# Python 3 (minimal)
sudo apt-get update -q
sudo apt-get install -y python3 python3-pip python3-serial --no-install-recommends

# pymavlink — build from source on Pi 1 (no prebuilt wheels)
pip3 install --no-cache-dir pymavlink pyserial

# Copy service file
sudo cp pi/droneresearch.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable droneresearch

# Serial port permission
sudo usermod -aG dialout pi

echo ""
echo "=== Done ==="
echo "Edit /etc/systemd/system/droneresearch.service to set your port."
echo "Then: sudo systemctl start droneresearch"
echo "Dashboard: http://$(hostname -I | cut -d' ' -f1):8080"
