#!/bin/bash

set -e    # Exit on error
set -x    # Print commands before executing them (helpful for debugging)

# Function to log steps
log_step() {
    echo "----------------------------------------"
    echo "🚀 $1"
    echo "----------------------------------------"
}

# 1. Clone ....................................................................
log_step "1/4 Cloning repository"
git submodule update

# Enter submodule directory
cd open-webui || exit 1

# 2. Install deps  ............................................................
log_step "2/4 Install deps"
npm install

# 3. Overload  ................................................................
log_step "3/4 Overload phase"

# Modify Dockerfile to increase Node.js memory limit
log_step "Updating Dockerfile configuration"
if ! grep -q "ENV NODE_OPTIONS=--max-old-space-size=4096" Dockerfile; then
    if ! sed -i '/WORKDIR \/app/i ENV NODE_OPTIONS=--max-old-space-size=4096' Dockerfile; then
        echo "❌ Failed to update Dockerfile"
        exit 1
    fi
    echo "✅ Added Node.js memory limit configuration"
else
    echo "ℹ️ Node.js memory limit configuration already exists"
fi

# 4. Customize ................................................................
log_step "4/4 Customization phase"

# TODO 2: copy customization/static/* content folder to open-webui/static/* inside the open-webui folder
