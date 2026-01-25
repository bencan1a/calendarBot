FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04

# Install Python 3.12 and development dependencies
RUN apt-get update && \
    apt-get install -y python3.12 python3.12-venv python3-pip && \
    rm -rf /var/lib/apt/lists/*

# Set python3.12 as the default python3
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1
