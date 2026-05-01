#!/usr/bin/env bash
# Generate item MD (Gemini) -> Imagen thumbnails -> optimize -> build JSON -> GCS image sync.
# Guides under app/content/guides/ are left untouched.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONUNBUFFERED=1

LIMIT="${CONTENT_LIMIT:-0}"
if [[ "${1:-}" != "" ]]; then
  LIMIT="$1"
fi

echo "== Item markdown (Gemini), limit=$LIMIT (0=all) =="
python3 script/item_generator.py --limit "$LIMIT"

echo "== Thumbnails (Vertex Imagen) =="
python3 script/fetch_images.py

echo "== Optimize JPEGs =="
python3 script/optimize_images.py

echo "== items_data.json =="
python3 script/build_data.py

GCS_BUCKET="${GCS_BUCKET:-gs://ok-project-assets/okcafejp}"
echo "== GCS rsync -> $GCS_BUCKET =="
gcloud storage rsync "$ROOT/app/static/images" "$GCS_BUCKET" --recursive --checksums-only
if command -v gsutil >/dev/null 2>&1; then
  gsutil -m acl ch -u AllUsers:R "$GCS_BUCKET/**" >/dev/null 2>&1 || true
fi

echo "Done."
