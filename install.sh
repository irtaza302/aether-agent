#!/bin/bash
set -e

echo "✨ Installing Aether AI Agent globally..."

if command -v pipx &> /dev/null; then
    pipx install -e . --force
    echo "✅ Aether installed successfully via pipx!"
else
    echo "⚠️  pipx not found. Installing via pip to your user directory."
    echo "   (Make sure ~/.local/bin is in your PATH)"
    pip install -e . --user
    echo "✅ Aether installed successfully!"
fi

echo "🚀 You can now run 'aether' from anywhere in your terminal."
