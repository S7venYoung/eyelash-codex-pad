#!/usr/bin/env bash
set -euo pipefail

ARCHITECTURE="${1:-arm64}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="Eyelash Codex Bridge"
EXECUTABLE="EyelashCodexBridge"
OUTPUT_DIR="${SCRIPT_DIR}/dist/${ARCHITECTURE}"
APP_DIR="${OUTPUT_DIR}/${APP_NAME}.app"

cd "${SCRIPT_DIR}"
swift build --configuration release --arch "${ARCHITECTURE}"
BIN_DIR="$(swift build --configuration release --arch "${ARCHITECTURE}" --show-bin-path)"

rm -rf "${OUTPUT_DIR}"
mkdir -p "${APP_DIR}/Contents/MacOS" "${APP_DIR}/Contents/Resources"
cp "${BIN_DIR}/${EXECUTABLE}" "${APP_DIR}/Contents/MacOS/${EXECUTABLE}"
cp "${SCRIPT_DIR}/Resources/Info.plist" "${APP_DIR}/Contents/Info.plist"
codesign --force --deep --sign - "${APP_DIR}"

cd "${OUTPUT_DIR}"
ditto -c -k --keepParent "${APP_NAME}.app" "Eyelash-Codex-Bridge-${ARCHITECTURE}.zip"
echo "Created ${OUTPUT_DIR}/Eyelash-Codex-Bridge-${ARCHITECTURE}.zip"
