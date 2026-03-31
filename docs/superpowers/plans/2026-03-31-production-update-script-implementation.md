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

- [ ] **Step 1: Write the failing smoke tests for usage, dirty-worktree rejection, success path, and rollback output**

```python
from __future__ import annotations

import os
import subprocess
from pathlib import Path


def test_update_prod_rejects_extra_arguments(tmp_path: Path):
    result = subprocess.run(
        ["bash", "update-prod.sh", "master", "extra"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "Usage:" in result.stdout + result.stderr


def test_update_prod_rejects_dirty_worktree(tmp_path: Path):
    result = run_update_script(tmp_path, git_status_output=" M services/reflex_api.py\n")
    assert result.returncode != 0
    assert "dirty" in (result.stdout + result.stderr).lower()


def test_update_prod_success_path_prints_backup_and_sha(tmp_path: Path):
    result = run_update_script(tmp_path, http_code="200")
    assert result.returncode == 0
    assert "Backup:" in result.stdout
    assert "Old SHA:" in result.stdout
    assert "New SHA:" in result.stdout


def test_update_prod_failure_prints_rollback_command(tmp_path: Path):
    result = run_update_script(tmp_path, http_code="500")
    assert result.returncode != 0
    assert "git reset --hard" in result.stdout + result.stderr
```

- [ ] **Step 2: Run the focused smoke tests to verify they fail**

Run: `D:\Coding\Test\test-reflex\.venv\Scripts\python.exe -m pytest tests/scripts/test_update_prod.py -v`

Expected: FAIL because `update-prod.sh` and its mocked-command behavior do not exist yet.

- [ ] **Step 3: Build the reusable mock-command test harness**

```python
def run_update_script(
    tmp_path: Path,
    *,
    git_status_output: str = "",
    http_code: str = "200",
) -> subprocess.CompletedProcess[str]:
    # create fake repo layout
    # write .env
    # copy update-prod.sh into temp repo
    # prepend fake git/docker/curl scripts to PATH
    # execute bash update-prod.sh
```

- [ ] **Step 4: Re-run the focused smoke tests to verify the harness is ready**

Run: `D:\Coding\Test\test-reflex\.venv\Scripts\python.exe -m pytest tests/scripts/test_update_prod.py -k "usage or dirty or success or rollback" -v`

Expected: still FAIL, but now on script behavior rather than missing harness pieces.

- [ ] **Step 5: Commit the failing test harness**

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
set -euo pipefail

TARGET_BRANCH="${1:-master}"
if [ "$#" -gt 1 ]; then
  echo "Usage: bash update-prod.sh [branch]"
  exit 1
fi
```

- [ ] **Step 2: Add prerequisite checks**

```bash
require_file ".env"
require_command git
require_command docker
docker compose version >/dev/null
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
BACKUP_DIR="/var/backups/test-reflex"
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

- [ ] **Step 8: Add unified error handling and rollback guidance**

```bash
print_rollback_instructions() {
  cat <<EOF
git checkout ${TARGET_BRANCH}
git reset --hard ${OLD_SHA}
docker compose build web
docker compose up -d web
EOF
}
```

- [ ] **Step 9: Run the focused smoke suite**

Run: `D:\Coding\Test\test-reflex\.venv\Scripts\python.exe -m pytest tests/scripts/test_update_prod.py -v`

Expected: PASS

- [ ] **Step 10: Run shell syntax validation**

Run: `bash -n update-prod.sh`

Expected: exit code `0`

- [ ] **Step 11: Commit the updater implementation**

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

- [ ] **Step 3: Inspect the final worktree**

Run: `git status --short`

Expected: no unintended files; only planned changes before final commit, then clean after commit.

- [ ] **Step 4: Summarize operator-facing usage**

```text
bash update-prod.sh
bash update-prod.sh <branch>
```

- [ ] **Step 5: Final commit if verification fixes were needed**

```bash
git add update-prod.sh tests/scripts/test_update_prod.py README.md
git commit -m "chore: finalize production update script verification"
```
