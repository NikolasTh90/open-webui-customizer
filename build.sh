#!/bin/bash

set -e    # Exit on error
#set -x    # Print commands before executing them (helpful for debugging)

# Function to log steps
log_step() {
    echo "----------------------------------------"
    echo "📦 $1"
    echo "----------------------------------------"
}

export NODE_OPTIONS=--max-old-space-size=4096

# Enter submodule directory
cd open-webui || exit 1

# 1. Build Dist Frontend App ..................................................
log_step "1/2 Building application"
if ! npm run build; then
    echo "❌ Failed to build Svelte application"
    exit 1
fi

# 2. Build Local Container ....................................................
log_step "2/2 Building container"
if ! ./run-compose.sh --build; then
    echo "❌ Failed to build Docker image"
    exit 1
fi

echo "✅ Build successfully"