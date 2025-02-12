# Use an official lightweight Python image as the base
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /workspace

# Install common dependencies for DevOps tasks
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    vim \
    nano \
    tree \
    iputils-ping \
    net-tools \
    dnsutils \
    procps \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Install Docker CLI (optional, but useful for debugging)
RUN curl -fsSL https://get.docker.com | sh

# Install Kubernetes CLI (kubectl)
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" \
    && chmod +x kubectl \
    && mv kubectl /usr/local/bin/

# Copy the entire repository into the container
COPY . .

# Expose a shell as an entry point
CMD ["/bin/bash"]
