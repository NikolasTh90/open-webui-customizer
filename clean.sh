#!/bin/bash

set -e    # Exit on error
set -x    # Print commands before executing them (helpful for debugging)

# Function to log steps
log_step() {
    echo "----------------------------------------"
    echo "🧹 $1"
    echo "----------------------------------------"
}

# 1. Clean submodule ............................................
log_step "Cleaning open-webui submodule"

# Enter submodule directory
cd open-webui || exit 1

# Stop any running containers and remove them
if command -v docker >/dev/null 2>&1; then
    docker-compose down --remove-orphans || true
fi

# Clean all untracked files and directories
git clean -fdx

# Reset all changes in the submodule
git reset --hard HEAD

# Return to parent directory
cd ..

# 2. Reset submodule to original state ..........................
log_step "Resetting submodule to original state"

# Reset submodule to its committed state
git submodule deinit -f open-webui
git submodule update --init --recursive

log_step "✅ Cleanup completed successfully"
