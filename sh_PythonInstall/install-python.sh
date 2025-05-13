#!/bin/bash
set -e

PYTHON_VERSION="3.12.3"

# Check internet connection
echo "🔍 Checking internet connection..."
if ! ping -q -c 1 -W 2 8.8.8.8 >/dev/null; then
    echo "❌ No internet connection. Please check your network settings."
    exit 1
fi

echo "✅ Internet connection: OK"
echo "📦 Installing Python $PYTHON_VERSION on CentOS 9..."

# Install required development tools and libraries
sudo dnf groupinstall -y "Development Tools"
sudo dnf install -y gcc openssl-devel bzip2-devel libffi-devel \
    wget make zlib-devel xz-devel readline-devel sqlite-devel

# Download and extract Python source
cd /usr/src
sudo wget https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tgz
sudo tar xzf Python-${PYTHON_VERSION}.tgz
cd Python-${PYTHON_VERSION}

# Build and install Python
sudo ./configure --enable-optimizations
sudo make -j$(nproc)
sudo make altinstall  # Avoid overwriting system python

# Verify installation
echo "✅ Installed Python version:"
/usr/local/bin/python3.12 --version

sudo rm /usr/bin/python
sudo ln -sf /usr/local/bin/python3.12 /usr/bin/python
#python --version
echo "🎉 Python $PYTHON_VERSION installed successfully!"

