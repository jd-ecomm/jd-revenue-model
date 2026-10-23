#!/usr/bin/env bash
# Rebuild, lock and stage the site. Needs: env PRM_PW (team password), node, python3, openssl.
# Usage: tools/publish.sh <kit-dir>   (run from the repo root)
set -euo pipefail
KIT="$1"; : "${PRM_PW:?set PRM_PW}"
python3 tools/build.py "$KIT" /tmp/prm_site.html
mkdir -p /tmp/prm_out
npx --yes staticrypt@3.5.4 /tmp/prm_site.html -p "$PRM_PW" -d /tmp/prm_out --short --remember 30 \
  --config .staticrypt.json \
  --template-title "Predictive Revenue Model" --template-instructions "JD Sports Canada eCommerce. Enter the team password." \
  --template-button "Open dashboard" --template-placeholder "Password" --template-remember "Remember me on this device for 30 days" \
  --template-error "Wrong password" --template-color-primary "#FFDE14" --template-color-secondary "#000000" >/dev/null
python3 tools/brand.py /tmp/prm_out/prm_site.html "$KIT"
cp /tmp/prm_out/prm_site.html index.html
# encrypted copy of the kit so the next run only needs the files that changed
tar -czf - -C "$KIT" . | openssl enc -aes-256-cbc -pbkdf2 -iter 600000 -salt -pass env:PRM_PW -out kit.tar.gz.enc
echo "staged index.html and kit.tar.gz.enc"
