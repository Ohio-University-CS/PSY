#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
FIREFOX_DIR="$SCRIPT_DIR/firefox"
OUT="$FIREFOX_DIR/firefox-clean.zip"

cd "$FIREFOX_DIR"
zip -r "$OUT" \
  manifest.json \
  background.js \
  content_script.js \
  popup.html \
  popup.css \
  popup.js \
  icons \
  -x "*.DS_Store" "__MACOSX/*" "._*" "*.zip"
