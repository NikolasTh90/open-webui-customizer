#!/bin/bash

set -e    # Exit on error
set -x    # Print commands before executing them (helpful for debugging)

# Function to log steps
log_step() {
    echo "----------------------------------------"
    echo "🚀 $1"
    echo "----------------------------------------"
}

# 1. Clone ......................................................
log_step "Cloning repository"
git submodule update
cd open-webui

# Get version after entering directory
VERSION=$(jq -r .version package.json)
echo "Building version: ${VERSION}"

# 2. Customize ..................................................
log_step "Customization phase"
# Do your Things!

# TODO 1: DO NOT FORGET TO INCLUDE IN dockerfile this: ENV NODE_OPTIONS=--max-old-space-size=4096
# TODO 2: copy static reference to static-inside

# 3. Build ......................................................
log_step "Building application"
if ! npm run build; then
    echo "❌ Failed to build Svelte application"
    exit 1
fi

if ! ./run-compose.sh --build; then
    echo "❌ Failed to build Docker image"
    exit 1
fi
