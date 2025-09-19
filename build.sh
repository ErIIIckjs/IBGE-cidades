#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status
set -e

echo "Installing Chrome and ChromeDriver..."
apt-get update
apt-get install -y google-chrome-stable

echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "Build completed successfully!"