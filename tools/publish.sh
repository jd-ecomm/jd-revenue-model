#!/usr/bin/env bash
# Rebuild and stage the site (no password lock). Needs: python3.
# Usage: tools/publish.sh <kit-dir>   (run from the repo root)
set -euo pipefail
KIT="$1"
python3 tools/build.py "$KIT" /tmp/prm_site.html
cp /tmp/prm_site.html index.html
echo "staged index.html"
