#!/bin/bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
echo "=== Building 公文助手 macOS .app ==="

# Step 1: Build frontend
echo "--- Building frontend ---"
cd "$PROJECT_ROOT/frontend"
pnpm install --frozen-lockfile 2>/dev/null || pnpm install
pnpm build

# Step 2: Build .app bundle
echo "--- Running PyInstaller ---"
cd "$PROJECT_ROOT"
pyinstaller doc-assistant.spec --clean --noconfirm

# Step 3: Verify
if [ -d "dist/公文助手.app" ]; then
    echo "=== Build successful: dist/公文助手.app ==="
    du -sh "dist/公文助手.app"
else
    echo "=== Build FAILED ==="
    exit 1
fi
