# Production Update Script Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a production-safe `update-prod.sh` script that updates an already-deployed Docker Compose installation, performs a PostgreSQL backup, restarts the `web` service, runs health checks, and prints rollback instructions on failure.

**Architecture:** Implement the updater as a single root-level Bash script with small focused shell functions for validation, git update, backup, deployment, and health checks. Verify it with a lightweight pytest smoke suite that runs the script against mocked `git`, `docker`, and `curl` binaries so failure paths and operator output are covered without touching a real production server.

**Tech Stack:** Bash, Docker Compose CLI, Git CLI, PostgreSQL `pg_dump`, pytest, Python subprocess/pathlib/tempfile

---

### Task 1: Add Script Smoke Test Harness

**Files:**
- Create: `D:\Coding\Test\test-reflex\tests\scripts\test_update_prod.py`
- Modify: `D:\Coding\Test\test-reflex\.gitignore` only if the new test creates local cache artifacts that should be ignored
- Reference: `D:\Coding\Test\test-reflex\docs\superpowers\specs\2026-03-31-production-update-script-design.md`

- [ ] **Step 1: Write the reusable mock-command test harness**

```python
def run_update_script(
    tmp_path: Path,
    *,
    argv: list[str] | None = None,
    git_status_output: str = "",
    http_code: str = "200",
) -> subprocess.CompletedProcess[str]:
    # create fake repo layout
    # write .env
    # copy update-prod.sh into temp repo
    # prepend fake git/docker/curl scripts to PATH
    # set BACKUP_DIR to a temp directory under tmp_path
    # execute bash update-prod.sh with argv
```

- [ ] **Step 2: Write the failing smoke tests for usage, dirty-worktree rejection, success path, redirect health-check success, and rollback output**

```python
from __future__ import annotations

import subprocess
from pathlib import Path


def test_update_prod_rejects_extra_arguments(tmp_path: Path):
    result = run_update_script(tmp_path, argv=["master", "extra"])
    assert result.returncode != 0
    assert "Usage:" in result.stdout + result.stderr


def test_update_prod_rejects_dirty_worktree(tmp_path: Path):
    result = run_update_script(tmp_path, git_status_output="?? stray-file.txt\n")
    assert result.returncode != 0
    assert "dirty" in (result.stdout + result.stderr).lower()


def test_update_prod_success_path_prints_backup_and_sha(tmp_path: Path):
    result = run_update_script(tmp_path, http_code="200")
    assert result.returncode == 0
    assert "Backup:" in result.stdout
    assert "Old SHA:" in result.stdout
    assert "New SHA:" in result.stdout
    assert "creating postgres backup" in result.stdout
    assert result.stdout.index("creating postgres backup") < result.stdout.index("building web image")


def test_update_prod_accepts_redirect_http_health(tmp_path: Path):
    result = run_update_script(tmp_path, http_code="302")
    assert result.returncode == 0


def test_update_prod_failure_prints_rollback_command(tmp_path: Path):
    result = run_update_script(tmp_path, http_code="500")
    assert result.returncode != 0
    assert "git checkout" in result.stdout + result.stderr
    assert "git reset --hard" in result.stdout + result.stderr
```

- [ ] **Step 3: Run the focused smoke tests to verify they fail**

Run: `D:\Coding\Test\test-reflex\.venv\Scripts\python.exe -m pytest tests/scripts/test_update_prod.py -v`

Expected: FAIL because `update-prod.sh` and its mocked-command behavior do not exist yet.

- [ ] **Step 4: Commit the failing test harness**

```bash
git add tests/scripts/test_update_prod.py
git commit -m "test: add production update script smoke harness"
```

### Task 2: Implement `update-prod.sh`

**Files:**
- Create: `D:\Coding\Test\test-reflex\update-prod.sh`
- Reference: `D:\Coding\Test\test-reflex\deploy.sh`
- Reference: `D:\Coding\Test\test-reflex\docker-compose.yml`
- Test: `D:\Coding\Test\test-reflex\tests\scripts\test_update_prod.py`

- [ ] **Step 1: Add script skeleton with strict shell options and argument parsing**

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

TARGET_BRANCH="${1:-master}"
if [ "$#" -gt 1 ]; then
  echo "Usage: bash update-prod.sh [branch]"
  exit 1
fi
```

- [ ] **Step 2: Add prerequisite checks**

```bash
require_file ".env"
require_file "docker-compose.yml"
require_command git
require_command docker
require_command curl
docker compose version >/dev/null
if [ "$(git rev-parse --show-toplevel)" != "$(pwd)" ]; then
  echo "[ERROR] Please run from the repository root."
  exit 1
fi
```

- [ ] **Step 3: Add strict clean-worktree enforcement**

```bash
if [ -n "$(git status --porcelain)" ]; then
  echo "[ERROR] Git worktree is dirty. Commit or stash changes before updating."
  exit 1
fi
```

- [ ] **Step 4: Add branch resolution and fast-forward-only update logic**

```bash
git fetch origin
OLD_BRANCH="$(git branch --show-current)"
OLD_SHA="$(git rev-parse HEAD)"

if git show-ref --verify --quiet "refs/heads/${TARGET_BRANCH}"; then
  git checkout "${TARGET_BRANCH}"
elif git show-ref --verify --quiet "refs/remotes/origin/${TARGET_BRANCH}"; then
  git checkout -b "${TARGET_BRANCH}" "origin/${TARGET_BRANCH}"
else
  echo "[ERROR] Branch origin/${TARGET_BRANCH} not found."
  exit 1
fi

git pull --ff-only origin "${TARGET_BRANCH}"
NEW_SHA="$(git rev-parse HEAD)"
```

- [ ] **Step 5: Add backup creation outside the repo worktree**

```bash
BACKUP_DIR="${BACKUP_DIR:-/var/backups/test-reflex}"
TIMESTAMP="$(date +%F-%H%M%S)"
BACKUP_FILE="${BACKUP_DIR}/reflex-${TIMESTAMP}.sql"
mkdir -p "${BACKUP_DIR}"
docker compose exec -T postgres pg_dump -U postgres reflex > "${BACKUP_FILE}"
```

- [ ] **Step 6: Add build and restart steps for the `web` service**

```bash
docker compose build web
docker compose up -d web
```

- [ ] **Step 7: Add bounded health checks**

```bash
wait_for_web_container
check_recent_logs_for_startup_failures
check_http_health "http://127.0.0.1:3000"
```

- [ ] **Step 8: Add explicit failure-state tracking**

```bash
CURRENT_STEP="startup"
OLD_BRANCH=""
OLD_SHA=""
NEW_SHA=""
BACKUP_FILE=""
```

- [ ] **Step 9: Add an `ERR` trap that prints failure summary and rollback guidance**

```bash
on_error() {
  local exit_code="$?"
  echo "[ERROR] Step failed: ${CURRENT_STEP}"
  echo "Old branch: ${OLD_BRANCH}"
  echo "Old SHA: ${OLD_SHA}"
  [ -n "${NEW_SHA}" ] && echo "New SHA: ${NEW_SHA}"
  [ -n "${BACKUP_FILE}" ] && echo "Backup: ${BACKUP_FILE}"
  print_rollback_instructions
  exit "${exit_code}"
}

trap on_error ERR

print_rollback_instructions() {
  cat <<EOF
git checkout ${OLD_BRANCH}
git reset --hard ${OLD_SHA}
docker compose build web
docker compose up -d web
EOF
}
```

- [ ] **Step 10: Update each major operation to set `CURRENT_STEP` before running**

```bash
CURRENT_STEP="fetching origin"
git fetch origin

CURRENT_STEP="creating postgres backup"
docker compose exec -T postgres pg_dump -U postgres reflex > "${BACKUP_FILE}"
```

- [ ] **Step 11: Make the script executable**

Run: `git update-index --chmod=+x update-prod.sh`

Expected: script is tracked as executable.

- [ ] **Step 12: Run the focused smoke suite**

Run: `D:\Coding\Test\test-reflex\.venv\Scripts\python.exe -m pytest tests/scripts/test_update_prod.py -v`

Expected: PASS

- [ ] **Step 13: Run shell syntax validation**

Run: `bash -n update-prod.sh`

Expected: exit code `0`

- [ ] **Step 14: Commit the updater implementation**

```bash
git add update-prod.sh tests/scripts/test_update_prod.py
git commit -m "feat: add production update script"
```

### Task 3: Document Operator Usage

**Files:**
- Modify: `D:\Coding\Test\test-reflex\README.md`
- Reference: `D:\Coding\Test\test-reflex\update-prod.sh`

- [ ] **Step 1: Add a short production update section near the existing production deployment notes**

```markdown
## Production Update

```bash
bash update-prod.sh
bash update-prod.sh master
```

The script requires a clean git worktree, creates a PostgreSQL backup, updates code, rebuilds the `web` service, and prints rollback instructions on failure.
```

- [ ] **Step 2: Run a focused content check**

Run: `rg -n "Production Update|update-prod.sh" README.md`

Expected: shows the new section and command examples.

- [ ] **Step 3: Commit the operator docs**

```bash
git add README.md
git commit -m "docs: add production update instructions"
```

### Task 4: Final Verification

**Files:**
- Verify: `D:\Coding\Test\test-reflex\update-prod.sh`
- Verify: `D:\Coding\Test\test-reflex\tests\scripts\test_update_prod.py`
- Verify: `D:\Coding\Test\test-reflex\README.md`

- [ ] **Step 1: Re-run the smoke suite**

Run: `D:\Coding\Test\test-reflex\.venv\Scripts\python.exe -m pytest tests/scripts/test_update_prod.py -v`

Expected: PASS

- [ ] **Step 2: Re-run shell syntax validation**

Run: `bash -n update-prod.sh`

Expected: exit code `0`

- [ ] **Step 3: Verify the executable bit is tracked**

Run: `git ls-files --stage update-prod.sh`

Expected: mode starts with `100755`.

- [ ] **Step 4: Inspect the final worktree**

Run: `git status --short`

Expected: no unintended files; only planned changes before final commit, then clean after commit.

- [ ] **Step 5: Summarize operator-facing usage**

```text
bash update-prod.sh
bash update-prod.sh <branch>
```

- [ ] **Step 6: Final commit if verification fixes were needed**

```bash
git add update-prod.sh tests/scripts/test_update_prod.py README.md
git commit -m "chore: finalize production update script verification"
```
