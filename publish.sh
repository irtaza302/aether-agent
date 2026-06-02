#!/bin/bash
set -e

if [ -d "venv" ]; then
    echo "🔌 Activating virtual environment..."
    source venv/bin/activate
fi

echo "🚀 Starting the Aether release process..."

echo "----------------------------------------"
echo "📦 1. Building and Publishing to PyPI"
echo "----------------------------------------"
rm -rf dist/ build/ *.egg-info
python3 setup.py sdist bdist_wheel
if command -v twine &> /dev/null; then
    echo "Uploading to PyPI..."
    twine upload dist/* || echo "⚠️ Twine upload failed or skipped. (Did you log in?)"
else
    echo "⚠️ Twine not found. Skipping PyPI upload."
    echo "   (Install it with: pip install twine)"
fi

echo ""
echo "----------------------------------------"
echo "📦 2. Publishing to NPM"
echo "----------------------------------------"
if command -v npm &> /dev/null; then
    cd npm-package
    npm publish || echo "⚠️ NPM publish failed or skipped. (Did you log in?)"
    cd ..
else
    echo "⚠️ NPM not found. Skipping."
fi

echo ""
echo "----------------------------------------"
echo "📦 3. Building macOS Binary (for Homebrew/Github)"
echo "----------------------------------------"
if command -v pyinstaller &> /dev/null; then
    pyinstaller aether.spec
    cd dist
    tar -czvf aether-macos.tar.gz aether
    echo "✅ macOS binary built at dist/aether-macos.tar.gz"
    echo "   (To update Homebrew, calculate the shasum with 'shasum -a 256 dist/aether-macos.tar.gz')"
    echo "   (Then update the sha256 and url in homebrew-aether/Formula/aether.rb)"
    cd ..
else
    echo "⚠️ PyInstaller not found. Skipping binary build."
    echo "   (Install it with: pip install pyinstaller)"
fi

echo ""
echo "----------------------------------------"
echo "📦 4. Tagging Release & Updating Homebrew"
echo "----------------------------------------"
VERSION=$(python3 -c "import aether; print(aether.__version__)")
TAG="v$VERSION"

if git rev-parse "$TAG" >/dev/null 2>&1; then
    echo "⚠️ Tag $TAG already exists, skipping git tagging."
else
    echo "Pushing tag $TAG..."
    git tag "$TAG"
    git push origin "$TAG"
    
    echo "Updating Homebrew formula..."
    # Wait a few seconds for GitHub to make the tarball available
    sleep 3
    URL="https://github.com/irtaza302/aether-agent/archive/refs/tags/${TAG}.tar.gz"
    SHA256=$(curl -sL "$URL" | shasum -a 256 | awk '{print $1}')
    
    cd homebrew-aether
    # Update formula on macOS using sed -i ''
    sed -i '' "s|url \".*\"|url \"${URL}\"|" Formula/aether.rb
    sed -i '' "s/sha256 \".*\"/sha256 \"${SHA256}\"/" Formula/aether.rb
    sed -i '' "s/version \".*\"/version \"${VERSION}\"/" Formula/aether.rb
    
    git commit -am "chore: Update formula to ${VERSION}" || true
    git push origin main || true
    cd ..
    echo "✅ Homebrew formula updated."
fi

echo ""
echo "🎉 Done! Everything has been prepared/published."
