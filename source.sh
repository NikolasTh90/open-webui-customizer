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
    if ! sed -i '/FROM.*node:.*AS build/,/WORKDIR \/app/ {/WORKDIR \/app/i ENV NODE_OPTIONS=--max-old-space-size=4096}' Dockerfile; then
        echo "❌ Failed to update Dockerfile"
        exit 1
    fi
    echo "✅ Added Node.js memory limit configuration"
else
    echo "ℹ️ Node.js memory limit configuration already exists"
fi

# 4. Customize ................................................................
log_step "4/4 Customization phase"

# Define source and destination directories
SRC_DIR="../customization/static/"
DEST_DIR="./static/"

# Ensure we're working with absolute paths
SRC_DIR=$(realpath "$SRC_DIR")
DEST_DIR=$(realpath "$DEST_DIR")

# Check if source directory exists
if [ ! -d "$SRC_DIR" ]; then
    echo "❌ Source directory $SRC_DIR not found"
    exit 1
fi

# Create destination directory if it doesn't exist
mkdir -p "$DEST_DIR"

# Function to check file structure consistency
check_structure() {
    local src="$1"
    local dest="$2"
    local inconsistencies=0

    # Check for files in source that don't exist in destination structure
    find "$src" -type f | while read -r srcfile; do
        # Get relative path
        relpath="${srcfile#$src}"
        destfile="$dest/$relpath"
        destdir=$(dirname "$destfile")

        if [ ! -d "$destdir" ]; then
            echo "⚠️  Warning: Directory structure mismatch for: $relpath"
            echo "   Source: $srcfile"
            echo "   Expected destination directory: $destdir"
            ((inconsistencies++))
        fi
    done

    return $inconsistencies
}

# Check structure consistency
echo "🔍 Checking structure consistency..."
check_structure "$SRC_DIR" "$DEST_DIR"
structure_status=$?

if [ $structure_status -gt 0 ]; then
    echo "⚠️  Found $structure_status potential structure inconsistencies"
    echo "💡 Review the warnings above before proceeding"
    read -p "Do you want to continue with the copy operation? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Operation cancelled by user"
        exit 1
    fi
fi

# Copy files with logging
echo "📁 Copying customization files..."
find "$SRC_DIR" -type f | while read -r srcfile; do
    relpath="${srcfile#$SRC_DIR}"
    destfile="$DEST_DIR/$relpath"
    destdir=$(dirname "$destfile")

    # Create destination directory if needed
    mkdir -p "$destdir"

    # Check if file exists in destination
    if [ -f "$destfile" ]; then
        if ! cmp -s "$srcfile" "$destfile"; then
            echo "🔄 Updating: $relpath"
            cp "$srcfile" "$destfile"
        else
            echo "✅ Unchanged: $relpath"
        fi
    else
        echo "➕ Adding new file: $relpath"
        cp "$srcfile" "$destfile"
    fi
done

echo "✅ Customization files copied successfully"
