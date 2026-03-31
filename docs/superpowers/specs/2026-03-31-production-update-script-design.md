# Production Update Script Design

## Summary

Add a dedicated production update script at the repository root named `update-prod.sh`.
The script is for post-deployment updates on an already-running production server that uses the existing Docker Compose deployment in this repository.

It must:
- default to updating `origin/master`
- allow passing a branch name override
- refuse to run if the git worktree is dirty
- create a timestamped PostgreSQL backup before rebuilding or restarting services
- record the previous and new git commit SHAs
- rebuild and restart the `web` service
- run post-update health checks
- print a rollback command on failure instead of auto-rolling back

It must not:
- replace or modify `deploy.sh`
- regenerate `.env`
- auto-stash local changes
- auto-rollback on failure

## Context

This repository already has:
- initial deployment via `deploy.sh`
- production runtime via `docker compose`
- a `web` service that runs Reflex in production
- PostgreSQL and Redis managed by Compose

The new script is specifically for safely updating code in production after the initial deployment is complete.

## Goals

- Make production updates repeatable and low-risk.
- Keep the workflow aligned with the repository's existing Docker Compose deployment.
- Give operators a simple, one-command update path.
- Preserve enough information to perform a fast manual rollback if the update fails.

## Non-Goals

- Initial server provisioning
- Docker installation
- `.env` generation
- Automatic rollback
- Multi-host orchestration
- Zero-downtime deployment
- Database schema migration framework beyond what the app already performs at startup

## User Interface

The script will be run from the repository root:

```bash
bash update-prod.sh
bash update-prod.sh master
bash update-prod.sh codex/agent-campaigns
```

Behavior:
- no argument: update `master`
- one argument: treat it as the target branch name
- any other usage: print help and exit non-zero

## Preconditions

The script assumes:
- it is executed on the production server
- the current directory is the repository root
- `.env` already exists
- `docker compose` is available
- the project has already been deployed successfully at least once
- the target branch exists on `origin`

If any precondition is not met, the script must exit with a clear error.

## Flow

1. Validate runtime prerequisites.
2. Validate clean git worktree.
3. Fetch from `origin`.
4. Resolve target branch.
5. Record current branch and current commit SHA as rollback metadata.
6. Fast-forward update the target branch from `origin/<branch>`.
7. Create a backup directory outside the git worktree if missing.
8. Create a timestamped PostgreSQL dump before any rebuild or restart step.
9. Rebuild the `web` image.
10. Restart `web` with Docker Compose.
11. Run health checks.
12. On success, print old SHA, new SHA, backup path, and service summary.
13. On failure, print a rollback command sequence and exit non-zero.

## Git Update Rules

- The script must fail if `git status --porcelain` is not empty.
- The script must use `git fetch origin`.
- The script must update by fast-forward only.
- If the local branch is different from the requested branch, the script may switch to the requested branch before fast-forwarding it.
- If the requested local branch does not exist but `origin/<branch>` exists, the script may create a local tracking branch.
- It must never use destructive cleanup against unrelated local changes.

## Backup Rules

Backups must not be written inside the git worktree.

Backups go to:

```text
/var/backups/test-reflex/reflex-YYYY-MM-DD-HHMMSS.sql
```

The backup command should use the existing Compose PostgreSQL service, for example:

```bash
docker compose exec -T postgres pg_dump -U postgres reflex > /var/backups/test-reflex/reflex-YYYY-MM-DD-HHMMSS.sql
```

If backup creation fails, the script must stop before rebuilding or restarting services.
It does not need to stop before `git fetch` or the fast-forward code update, but it must stop before any container rebuild or restart.

## Deployment Rules

The update path should target the existing production runtime:

```bash
docker compose build web
docker compose up -d web
```

This keeps the update scope narrow and avoids unnecessary churn in PostgreSQL and Redis containers.

## Health Checks

The script should run layered checks after restart:

1. Container check
   - verify `web` is up via `docker compose ps web`
2. Log check
   - inspect recent `web` logs and fail on obvious startup crashes
3. HTTP check
   - request at least one local endpoint such as:
     - `http://127.0.0.1:3000`
     - optionally `http://127.0.0.1:8000`

HTTP success means receiving a reachable response from the local service, such as HTTP `200`, `301`, `302`, `307`, or `308`.

Obvious startup failure log patterns include:
- Python tracebacks
- unhandled exceptions
- bind/listen failures
- database connection failures during startup
- process exit or crash-loop messages

Health checks must be bounded with retry loops and short waits so startup delays do not cause immediate false failures.

## Failure Handling

On failure, the script must:
- print the failed step
- print the old SHA
- print the new SHA if it was reached
- print the backup file path if backup succeeded
- print a rollback command sequence
- exit non-zero

Rollback instructions should be explicit, for example:

```bash
git checkout <branch>
git reset --hard <old_sha>
docker compose build web
docker compose up -d web
```

The script must not execute rollback automatically.

## Logging

The script should print concise progress messages, for example:
- checking prerequisites
- checking git status
- fetching origin
- switching branch
- creating backup
- building web image
- restarting web
- running health checks
- update successful

All messages should be operator-friendly and suitable for direct terminal use.

## Security and Safety

- Do not rewrite `.env`.
- Do not print secrets.
- Do not expose PostgreSQL or Redis ports.
- Do not run if the worktree is dirty.
- Do not auto-merge or resolve git conflicts.
- Do not auto-rollback.

## Files

Add:
- `update-prod.sh`

Do not modify:
- `deploy.sh`

May update:
- `README.md` only if a short production update section is needed to document the new script

## Testing and Verification

Implementation must be verified by:
- shell syntax check for `update-prod.sh`
- dry run or command-path validation where feasible
- at least one focused test or smoke verification of generated rollback/backup path behavior if practical in the current repo
- manual invocation guidance for operators

Minimum success evidence before completion:
- script file exists at repo root
- script is executable
- script validates a clean worktree
- script prints usage/help on invalid arguments
- script performs backup before rebuild logic in the happy path
- script prints rollback instructions on failure paths

## Acceptance Criteria

- Running `bash update-prod.sh` updates `master` from `origin/master`.
- Running `bash update-prod.sh <branch>` updates the specified branch from `origin/<branch>`.
- The script exits early if the repository has uncommitted or untracked changes.
- The script creates a timestamped SQL backup outside the git worktree and before rebuild/restart.
- The script rebuilds and restarts the `web` service.
- The script performs post-update health checks.
- The script prints old/new commit SHAs and backup location on success.
- The script prints a concrete rollback command sequence on failure.
- The script leaves `deploy.sh` unchanged.
