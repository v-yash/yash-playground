FROM python:3.11-slim

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

RUN pip install flask

# Install Docker CLI (optional, but useful for debugging)
# RUN curl -fsSL https://get.docker.com | sh

# Install Kubernetes CLI (kubectl)
# RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" \
#     && chmod +x kubectl \
#     && mv kubectl /usr/local/bin/

# Copy the entire repository into the container
COPY . .

RUN pip install -r requirements.txt

# Expose port 5000 for Flask
EXPOSE 5000

# Run the web app
CMD ["python", "webapp/app.py"]
