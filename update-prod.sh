#!/usr/bin/env bash
set -Eeuo pipefail

CURRENT_STEP="initialization"
TARGET_BRANCH="master"
OLD_BRANCH=""
OLD_SHA=""
NEW_SHA=""
BACKUP_PATH=""

usage() {
  cat <<'USAGE'
Usage: ./update-prod.sh [branch]

Updates production from git and restarts only the web service.
If no branch is provided, master is used.
USAGE
}

print_rollback_instructions() {
  echo ""
  echo "Rollback instructions (manual):"
  if [[ -n "${OLD_BRANCH:-}" && "${OLD_BRANCH}" != "(detached-head)" ]]; then
    echo "  git checkout \"$OLD_BRANCH\""
  fi
  if [[ -n "${OLD_SHA:-}" ]]; then
    echo "  git reset --hard \"$OLD_SHA\""
  else
    echo "  git reset --hard <previous_sha>"
  fi
  if [[ -n "${BACKUP_PATH:-}" ]]; then
    echo "  docker compose exec -T postgres psql -U postgres reflex < \"$BACKUP_PATH\""
  fi
  echo "  docker compose up -d web"
}

on_error() {
  local exit_code=$?
  echo "[ERROR] Step failed: ${CURRENT_STEP}" >&2
  print_rollback_instructions >&2
  exit "$exit_code"
}

trap on_error ERR

require_command() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "[ERROR] Missing required command: $cmd" >&2
    return 1
  fi
}

fail_step() {
  echo "[ERROR] $*" >&2
  return 1
}

if [[ $# -gt 1 ]]; then
  usage >&2
  exit 1
fi

if [[ $# -eq 1 ]]; then
  TARGET_BRANCH="$1"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "$PWD" != "$SCRIPT_DIR" ]]; then
  echo "[ERROR] Run this script from repository root: $SCRIPT_DIR" >&2
  exit 1
fi

if [[ ! -d .git ]]; then
  echo "[ERROR] .git directory not found. Must run at repo root." >&2
  exit 1
fi

if [[ ! -f .env ]]; then
  echo "[ERROR] Missing required file: .env" >&2
  exit 1
fi

if [[ ! -f docker-compose.yml ]]; then
  echo "[ERROR] Missing required file: docker-compose.yml" >&2
  exit 1
fi

CURRENT_STEP="checking required commands"
require_command git
require_command docker
require_command curl

CURRENT_STEP="checking clean git worktree"
WORKTREE_STATUS="$(git status --porcelain)"
if [[ -n "$WORKTREE_STATUS" ]]; then
  echo "[ERROR] Working tree is not clean." >&2
  echo "$WORKTREE_STATUS" >&2
  exit 1
fi

CURRENT_STEP="capturing current git state"
OLD_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
OLD_SHA="$(git rev-parse HEAD)"

CURRENT_STEP="fetching origin"
git fetch origin

CURRENT_STEP="resolving branch ${TARGET_BRANCH}"
if git show-ref --verify --quiet "refs/heads/${TARGET_BRANCH}"; then
  git checkout "${TARGET_BRANCH}"
else
  git checkout -b "${TARGET_BRANCH}" "origin/${TARGET_BRANCH}"
fi

CURRENT_STEP="fast-forwarding branch ${TARGET_BRANCH}"
git merge --ff-only "origin/${TARGET_BRANCH}"
NEW_SHA="$(git rev-parse "origin/${TARGET_BRANCH}")"

CURRENT_STEP="loading environment"
set -a
# shellcheck disable=SC1091
source .env
set +a
HEALTHCHECK_URL="${HEALTHCHECK_URL:-http://127.0.0.1:8000/health}"

BACKUP_DIR="${BACKUP_DIR:-/var/backups/test-reflex}"
CURRENT_STEP="creating backup directory"
mkdir -p "$BACKUP_DIR"
BACKUP_PATH="${BACKUP_DIR}/reflex-$(date +%Y%m%d-%H%M%S)-${OLD_SHA:0:7}.sql"

CURRENT_STEP="creating backup"
docker compose exec -T postgres pg_dump -U postgres reflex >"$BACKUP_PATH"

CURRENT_STEP="building web service"
docker compose build web

CURRENT_STEP="restarting web service"
docker compose up -d web

CURRENT_STEP="checking container status"
docker compose ps web >/dev/null

CURRENT_STEP="checking service logs"
docker compose logs --tail 80 web >/dev/null

CURRENT_STEP="checking http health"
HTTP_CODE="$(curl -sS -o /dev/null -w '%{http_code}' "$HEALTHCHECK_URL")"
if [[ ! "$HTTP_CODE" =~ ^[0-9]{3}$ ]]; then
  fail_step "Invalid HTTP status code: $HTTP_CODE"
fi

if (( HTTP_CODE < 200 || HTTP_CODE >= 400 )); then
  fail_step "Health check failed for $HEALTHCHECK_URL (HTTP $HTTP_CODE)."
fi

echo "Production update completed successfully."
echo "Backup: $BACKUP_PATH"
echo "Previous SHA: $OLD_SHA"
echo "Updated SHA: $NEW_SHA"
