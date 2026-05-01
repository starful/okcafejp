#!/bin/bash
# OKCafeJP deployment helper script.
set -euo pipefail

GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
PROJECT_NAME="${PROJECT_NAME:-okcafejp}"
SERVICE_URL="${SERVICE_URL:-https://okcafejp.net}"
GCS_BUCKET="${GCS_BUCKET:-gs://ok-project-assets/${PROJECT_NAME}}"
LOCAL_IMAGES="app/static/images"
GCP_PROJECT_ID="${GCP_PROJECT_ID:-starful-258005}"

MODE="full"
DO_GIT=false
DO_CLOUD_DEPLOY=false
CONTENT_LIMIT="${CONTENT_LIMIT:-0}"
GUIDE_LIMIT="${GUIDE_LIMIT:-3}"

print_step() {
    echo ""
    echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}${CYAN}  $1${NC}"
    echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}
print_ok()   { echo -e "${GREEN}  ✅ $1${NC}"; }
print_info() { echo -e "  ℹ️  $1"; }

usage() {
    cat <<'EOF'
Usage: ./deploy.sh [MODE] [OPTIONS]

Modes (default: full)
  --full           Sync images + generate content + image process + build
  --content-only   Generate guides/items markdown + build only
  --deploy-only    Trigger Cloud Build deploy only

Options
  --with-git       Commit and push generated changes
  --with-deploy    Trigger deploy after selected mode
  --help           Show this help

Environment overrides
  PROJECT_NAME     Default: okcafejp
  SERVICE_URL      Default: https://okcafejp.net
  GCS_BUCKET       Default: gs://ok-project-assets/${PROJECT_NAME}
  GCP_PROJECT_ID   Default: starful-258005
  CONTENT_LIMIT    Default: 0 (all items.csv rows; set e.g. 10 to cap)
  GUIDE_LIMIT      Default: 3
EOF
}

require_cmd() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "Missing required command: $1" >&2
        exit 1
    fi
}

sync_cloud_images_to_local() {
    print_step "STEP A: Cloud -> Local image sync"
    mkdir -p "$LOCAL_IMAGES"
    gcloud storage rsync "$GCS_BUCKET" "$LOCAL_IMAGES" --recursive
    print_ok "Cloud image sync completed"
}

generate_content() {
    print_step "STEP B: Generate content markdown"
    print_info "Guide limit: GUIDE_LIMIT=${GUIDE_LIMIT} (guide_generator). Item rows: CONTENT_LIMIT=${CONTENT_LIMIT} (0=all)."
    python3 script/guide_generator.py
    python3 script/item_generator.py --limit "${CONTENT_LIMIT}"
    print_ok "Content generation completed"
}

process_and_upload_images() {
    print_step "STEP C: Process and upload images"
    python3 script/fetch_images.py
    python3 script/optimize_images.py
    gcloud storage rsync "$LOCAL_IMAGES" "$GCS_BUCKET" --recursive --checksums-only
    gsutil -m acl ch -u AllUsers:R "$GCS_BUCKET/**" >/dev/null 2>&1 || true
    print_ok "Image upload and ACL update completed"
}

build_data() {
    print_step "STEP D: Build JSON and sitemap"
    python3 script/build_data.py
    print_ok "Data build completed"
}

git_push_changes() {
    print_step "STEP E: Commit and push changes"
    git add .
    if ! git diff-index --quiet HEAD --; then
        local commit_msg
        commit_msg="chore: update generated contents $(date '+%Y-%m-%d %H:%M')"
        git commit -m "$commit_msg"
        git push origin main
        print_ok "Git push completed"
    else
        print_info "No changes detected, skipping git push"
    fi
}

deploy_cloud_run() {
    print_step "STEP F: Trigger Cloud Build"
    gcloud builds submit --project "$GCP_PROJECT_ID"
    print_ok "Cloud Build deployment completed"
}

for arg in "$@"; do
    case "$arg" in
        --full) MODE="full" ;;
        --content-only) MODE="content-only" ;;
        --deploy-only) MODE="deploy-only" ;;
        --with-git) DO_GIT=true ;;
        --with-deploy) DO_CLOUD_DEPLOY=true ;;
        --help|-h) usage; exit 0 ;;
        *)
            echo "Unknown argument: $arg" >&2
            usage
            exit 1
            ;;
    esac
done

cd "$PROJECT_ROOT"
START_TIME=$SECONDS

print_info "Project: $PROJECT_NAME"
print_info "Service URL: $SERVICE_URL"
print_info "Mode: $MODE"
print_info "Bucket: $GCS_BUCKET"
print_info "GCP project: $GCP_PROJECT_ID"
print_info "Limits: content=${CONTENT_LIMIT}, guide=${GUIDE_LIMIT}"

require_cmd python3
require_cmd gcloud

case "$MODE" in
    full)
        require_cmd gsutil
        sync_cloud_images_to_local
        generate_content
        process_and_upload_images
        build_data
        ;;
    content-only)
        generate_content
        build_data
        ;;
    deploy-only)
        DO_CLOUD_DEPLOY=true
        ;;
esac

if [ "$DO_GIT" = true ]; then
    require_cmd git
    git_push_changes
fi

if [ "$DO_CLOUD_DEPLOY" = true ]; then
    deploy_cloud_run
fi

ELAPSED=$((SECONDS - START_TIME))
echo -e "\n${BOLD}${GREEN}Done in $((ELAPSED/60))m $((ELAPSED%60))s${NC}"
