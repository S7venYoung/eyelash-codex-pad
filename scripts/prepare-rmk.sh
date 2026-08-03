#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
vendor_dir="$repo_root/firmware/codex/vendor/rmk"
rmk_rev="936a2a828fddc195d20e42bd952119cd3afa8172"

rm -rf "$vendor_dir"
mkdir -p "$vendor_dir"
curl -L --fail "https://github.com/HaoboGu/rmk/archive/$rmk_rev.tar.gz" \
  | tar -xz --strip-components=1 -C "$vendor_dir"
cp -R "$repo_root/rmk-overrides/rmk/src/." "$vendor_dir/rmk/src/"

