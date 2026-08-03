#!/usr/bin/env bash
set -euo pipefail

FREEMICRO_COMMIT="64258eb6cc3312a43f9f9f86d87e55e0b609ccc5"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
SOURCE_DIR="${REPO_DIR}/.freemicro-src"
VENV_DIR="${REPO_DIR}/.venv-freemicro"
ARCHIVE_URL="https://github.com/eliBenven/freemicro/archive/${FREEMICRO_COMMIT}.tar.gz"

if [[ ! -f "${SOURCE_DIR}/src/freemicro/device/codex_micro.py" ]]; then
  TEMP_DIR="$(mktemp -d)"
  trap 'rm -rf "${TEMP_DIR}"' EXIT
  mkdir -p "${SOURCE_DIR}"
  echo "Downloading pinned FreeMicro revision ${FREEMICRO_COMMIT}..."
  curl --fail --location --silent --show-error "${ARCHIVE_URL}" \
    | tar -xz -C "${SOURCE_DIR}" --strip-components=1
fi

python3 "${SCRIPT_DIR}/patch_freemicro.py" "${SOURCE_DIR}"
python3 "${SCRIPT_DIR}/patch_freemicro.py" --check "${SOURCE_DIR}"

python3 -m venv "${VENV_DIR}"
"${VENV_DIR}/bin/python" -m pip install --upgrade pip
"${VENV_DIR}/bin/python" -m pip install --editable "${SOURCE_DIR}"

echo
echo "FreeMicro compatibility build installed."
echo "Try: ${VENV_DIR}/bin/freemicro keys --dry-run"
