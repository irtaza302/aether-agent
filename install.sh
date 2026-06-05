#!/bin/bash
set -e

echo "✨ Installing Aizen AI Agent globally..."

if command -v pipx &> /dev/null; then
    pipx install -e . --force
    echo "✅ Aizen installed successfully via pipx!"
else
    echo "⚠️  pipx not found. Installing via pip to your user directory."
    echo "   (Make sure ~/.local/bin is in your PATH)"
    pip install -e . --user
    echo "✅ Aizen installed successfully!"
fi

echo "🚀 You can now run 'aizen' from anywhere in your terminal."
