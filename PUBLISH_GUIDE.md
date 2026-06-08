# Aizen Release & Publishing Guide

This guide explains how to release a new version of the Aizen AI Agent and publish it to all supported package managers (PyPI, NPM, and Homebrew).

## Prerequisites

Before running a release, ensure you have the following installed in your virtual environment:
```bash
source .venv/bin/activate
pip install build twine pyinstaller pytest ruff
```

## The Automated Script: `publish.sh`

Aizen includes a `publish.sh` script that automates the release process. 

Before running it, make sure you have:
1. Updated the version number in `pyproject.toml`.
2. Updated the fallback version in `aizen/config.py`.
3. Updated the version in `npm-package/package.json`.
4. Committed all your changes to Git.

### What the script does:
1. **Tests & Linting**: Runs `pytest` and `ruff` to ensure everything is stable. If tests fail, the script aborts.
2. **PyPI Build & Publish**: Uses the `build` module to package the source distribution (sdist) and wheel. It then uses `twine` to upload to PyPI.
3. **NPM Publish**: Changes to the `npm-package` directory and runs `npm publish`.
4. **macOS Binary**: Uses `pyinstaller` to compile Aizen into a standalone executable.
5. **GitHub Tagging**: Tags the current Git commit with `vX.X.X` and pushes the tag to GitHub.
6. **Homebrew Formula**: Calculates the SHA256 of the GitHub release tarball, updates the `homebrew-aizen/Formula/aizen.rb` file, and pushes the commit to the Homebrew tap repository.

## Manual Interventions (Authentication)

Because package managers often require interactive 2FA/Authentication, the `publish.sh` script might fail on the PyPI or NPM steps. The script is designed to safely skip these if they fail and continue to the GitHub tagging and Homebrew update.

### 1. PyPI Authentication Fails (`403 Forbidden`)
If PyPI fails, you need to configure your PyPI token.
- Generate an API token from your PyPI account.
- Add it to `~/.pypirc`:
  ```ini
  [pypi]
  username = __token__
  password = pypi-your-token-here
  ```
- **Manual Retry**: `twine upload dist/aizen_ai_cli*`

### 2. NPM Authentication Fails (`EOTP`)
If NPM fails because it requires a One-Time Password (2FA), the script cannot pass this automatically.
- **Manual Retry**: 
  ```bash
  cd npm-package
  npm publish
  ```
  This will open a browser window for you to authenticate, or you can run `npm publish --otp=YOUR_CODE_HERE`.

## Summary Checklist
- [ ] Update version in 3 files (`pyproject.toml`, `aizen/config.py`, `npm-package/package.json`)
- [ ] Ensure `MANIFEST.in` includes `requirements.txt`
- [ ] Commit all code
- [ ] Run `./publish.sh`
- [ ] If PyPI/NPM fail due to auth, run them manually: `twine upload dist/aizen_ai_cli*` and `cd npm-package && npm publish`
