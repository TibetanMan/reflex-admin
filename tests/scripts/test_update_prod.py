from __future__ import annotations

import os
import shutil
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_SCRIPT = REPO_ROOT / "update-prod.sh"

DEFAULT_GIT_SCRIPT = dedent(
    """
    state_file="${FAKE_GIT_STATE_FILE:-}"
    current_sha="${FAKE_GIT_OLD_SHA:-1111111111111111111111111111111111111111}"
    new_sha="${FAKE_GIT_NEW_SHA:-2222222222222222222222222222222222222222}"

    if [[ -n "$state_file" && ! -f "$state_file" ]]; then
      printf '%s\\n' "$current_sha" >"$state_file"
    fi

    if [[ -n "$state_file" && -f "$state_file" ]]; then
      current_sha="$(cat "$state_file")"
    fi

    args=("$@")
    cmd_index=0
    while [[ "$cmd_index" -lt "${#args[@]}" ]]; do
      token="${args[$cmd_index]}"
      case "$token" in
        --)
          cmd_index=$((cmd_index + 1))
          break
          ;;
        -C|--git-dir|--work-tree|--namespace|--exec-path|--super-prefix|-c|--config-env)
          cmd_index=$((cmd_index + 2))
          ;;
        --config-env=*)
          cmd_index=$((cmd_index + 1))
          ;;
        -*)
          cmd_index=$((cmd_index + 1))
          ;;
        *)
          break
          ;;
      esac
    done

    cmd1="${args[$cmd_index]-}"
    cmd2="${args[$((cmd_index + 1))]-}"
    cmd3="${args[$((cmd_index + 2))]-}"

    if [[ "$cmd1" == "status" && "$cmd2" == "--porcelain" ]]; then
      printf '%s' "${FAKE_GIT_STATUS:-}"
      exit "${FAKE_GIT_STATUS_EXIT:-0}"
    fi

    if [[ "$cmd1" == "rev-parse" && "$cmd2" == "--abbrev-ref" ]]; then
      printf '%s\\n' "${FAKE_GIT_BRANCH:-master}"
      exit 0
    fi

    if [[ "$cmd1" == "rev-parse" && "$cmd2" == "--short" ]]; then
      printf '%s\\n' "${current_sha:0:7}"
      exit 0
    fi

    if [[ "$cmd1" == "rev-parse" && "${cmd2-}" == origin/* ]]; then
      printf '%s\\n' "$new_sha"
      exit 0
    fi

    if [[ "$cmd1" == "rev-parse" ]]; then
      printf '%s\\n' "$current_sha"
      exit 0
    fi

    if [[ "$cmd1" == "pull" ]]; then
      if [[ -n "$state_file" ]]; then
        printf '%s\\n' "$new_sha" >"$state_file"
      fi
      exit 0
    fi

    if [[ "$cmd1" == "fetch" ]]; then
      exit 0
    fi

    if [[ "$cmd1" == "reset" && "$cmd2" == "--hard" && -n "$cmd3" ]]; then
      if [[ -n "$state_file" ]]; then
        printf '%s\\n' "$cmd3" >"$state_file"
      fi
      exit 0
    fi

    if [[ "$cmd1" == "checkout" || "$cmd1" == "clean" || "$cmd1" == "restore" ]]; then
      exit 0
    fi

    printf '%s' "${FAKE_GIT_FALLBACK_OUTPUT:-}"
    exit "${FAKE_GIT_FALLBACK_EXIT:-0}"
    """
).strip()

DEFAULT_DOCKER_SCRIPT = dedent(
    """
    if [[ -n "${FAKE_DOCKER_LOG:-}" ]]; then
      printf '%s\\n' "$*" >>"${FAKE_DOCKER_LOG}"
    fi

    if [[ "${1-}" == "compose" ]]; then
      exit "${FAKE_DOCKER_COMPOSE_EXIT:-0}"
    fi

    exit "${FAKE_DOCKER_EXIT:-0}"
    """
).strip()

DEFAULT_CURL_SCRIPT = dedent(
    """
    if [[ -n "${FAKE_CURL_LOG:-}" ]]; then
      printf '%s\\n' "$*" >>"${FAKE_CURL_LOG}"
    fi

    printf '%s' "${FAKE_CURL_HTTP_CODE:-200}"
    exit "${FAKE_CURL_EXIT:-0}"
    """
).strip()


@dataclass
class ScriptRun:
    completed: subprocess.CompletedProcess[str]
    repo_root: Path
    backup_dir: Path
    docker_log: Path
    curl_log: Path
    git_state_file: Path
    source_script_found: bool


def _write_executable(path: Path, body: str) -> None:
    path.write_text(
        "#!/usr/bin/env bash\nset -eu\n" + body.strip() + "\n",
        encoding="utf-8",
        newline="\n",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _find_bash() -> str | None:
    bash_path = shutil.which("bash")
    bash_name = Path(bash_path).name.lower() if bash_path else ""
    if os.name != "nt" or (bash_path and bash_name != "bash.exe"):
        return bash_path

    preferred_candidates = [
        Path(r"D:\Coding\Git\bin\bash.exe"),
        Path(r"D:\Coding\Git\usr\bin\bash.exe"),
        Path(r"C:\Program Files\Git\bin\bash.exe"),
        Path(r"C:\Program Files\Git\usr\bin\bash.exe"),
    ]
    for candidate in preferred_candidates:
        if candidate.exists():
            return str(candidate)

    return bash_path


def run_update_script(
    tmp_path: Path,
    argv: list[str],
    *,
    env_overrides: dict[str, str] | None = None,
    git_script: str = DEFAULT_GIT_SCRIPT,
    docker_script: str = DEFAULT_DOCKER_SCRIPT,
    curl_script: str = DEFAULT_CURL_SCRIPT,
) -> ScriptRun:
    bash_path = _find_bash()
    if not bash_path:
        pytest.skip("bash is required for update-prod.sh smoke tests")

    repo_root = tmp_path / "fake-repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    (repo_root / ".env").write_text(
        "APP_ENV=test\nHEALTHCHECK_URL=http://127.0.0.1:18080/health\n",
        encoding="utf-8",
        newline="\n",
    )
    (repo_root / "docker-compose.yml").write_text("services: {}\n", encoding="utf-8", newline="\n")

    source_script_found = SOURCE_SCRIPT.exists()
    if source_script_found:
        for shell_file in REPO_ROOT.glob("*.sh"):
            target = repo_root / shell_file.name
            shutil.copy2(shell_file, target)
            target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    fake_bin = repo_root / "fake-bin"
    fake_bin.mkdir()
    _write_executable(fake_bin / "git", git_script)
    _write_executable(fake_bin / "docker", docker_script)
    _write_executable(fake_bin / "curl", curl_script)
    fake_env = repo_root / ".fake-tools-env.sh"
    fake_env.write_text(
        dedent(
            f"""
            #!/usr/bin/env bash
            git() {{
              (
                set -eu
                {git_script}
              )
            }}

            docker() {{
              (
                set -eu
                {docker_script}
              )
            }}

            curl() {{
              (
                set -eu
                {curl_script}
              )
            }}
            """
        ).strip()
        + "\n",
        encoding="utf-8",
        newline="\n",
    )

    backup_dir = repo_root / "backups"
    backup_dir.mkdir()
    git_state_file = repo_root / "git-state.txt"
    docker_log = repo_root / "docker.log"
    curl_log = repo_root / "curl.log"

    env = os.environ.copy()
    env["PATH"] = str(fake_bin) + os.pathsep + env.get("PATH", "")
    env["BACKUP_DIR"] = str(backup_dir)
    env["FAKE_GIT_STATE_FILE"] = str(git_state_file)
    env["FAKE_DOCKER_LOG"] = str(docker_log)
    env["FAKE_CURL_LOG"] = str(curl_log)
    env["BASH_ENV"] = str(fake_env)
    if env_overrides:
        env.update(env_overrides)

    completed = subprocess.run(
        [bash_path, "update-prod.sh", *argv],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    return ScriptRun(
        completed=completed,
        repo_root=repo_root,
        backup_dir=backup_dir,
        docker_log=docker_log,
        curl_log=curl_log,
        git_state_file=git_state_file,
        source_script_found=source_script_found,
    )


def _assert_missing_script_failure(run: ScriptRun) -> None:
    if run.source_script_found:
        return
    combined = f"{run.completed.stdout}\n{run.completed.stderr}".lower()
    assert run.completed.returncode != 0
    assert "update-prod.sh" in combined
    pytest.fail("update-prod.sh is missing at repository root; add the script to satisfy this smoke suite.")


def test_update_prod_rejects_extra_argument_with_usage(tmp_path: Path) -> None:
    run = run_update_script(tmp_path, ["master", "unexpected"])
    _assert_missing_script_failure(run)

    combined = f"{run.completed.stdout}\n{run.completed.stderr}"
    assert run.completed.returncode != 0
    assert "usage" in combined.lower()


def test_update_prod_rejects_dirty_worktree_from_untracked_status(tmp_path: Path) -> None:
    run = run_update_script(tmp_path, [], env_overrides={"FAKE_GIT_STATUS": "?? stray-file.txt\n"})
    _assert_missing_script_failure(run)

    combined = f"{run.completed.stdout}\n{run.completed.stderr}"
    assert run.completed.returncode != 0
    assert "stray-file.txt" in combined or "dirty" in combined.lower() or "untracked" in combined.lower()


def test_update_prod_success_prints_backup_and_old_new_sha(tmp_path: Path) -> None:
    old_sha = "1111111111111111111111111111111111111111"
    new_sha = "2222222222222222222222222222222222222222"
    run = run_update_script(
        tmp_path,
        [],
        env_overrides={
            "FAKE_GIT_STATUS": "",
            "FAKE_GIT_OLD_SHA": old_sha,
            "FAKE_GIT_NEW_SHA": new_sha,
            "FAKE_CURL_HTTP_CODE": "200",
        },
    )
    _assert_missing_script_failure(run)

    combined = f"{run.completed.stdout}\n{run.completed.stderr}".lower()
    assert run.completed.returncode == 0
    assert "backup" in combined
    assert old_sha in combined or old_sha[:7] in combined
    assert new_sha in combined or new_sha[:7] in combined
    assert any(run.backup_dir.iterdir())
    docker_log = run.docker_log.read_text(encoding="utf-8") if run.docker_log.exists() else ""
    assert "compose build web" in docker_log
    assert "compose up -d web" in docker_log
    assert docker_log.index("exec -T postgres pg_dump -U postgres reflex") < docker_log.index("compose build web")


def test_update_prod_accepts_http_redirect_healthcheck_302(tmp_path: Path) -> None:
    run = run_update_script(
        tmp_path,
        [],
        env_overrides={
            "FAKE_GIT_STATUS": "",
            "FAKE_CURL_HTTP_CODE": "302",
        },
    )
    _assert_missing_script_failure(run)

    combined = f"{run.completed.stdout}\n{run.completed.stderr}".lower()
    assert run.completed.returncode == 0
    curl_log = run.curl_log.read_text(encoding="utf-8") if run.curl_log.exists() else ""
    assert curl_log


def test_update_prod_failure_path_prints_rollback_command(tmp_path: Path) -> None:
    old_sha = "1111111111111111111111111111111111111111"
    run = run_update_script(
        tmp_path,
        [],
        env_overrides={
            "FAKE_GIT_STATUS": "",
            "FAKE_GIT_OLD_SHA": old_sha,
            "FAKE_GIT_NEW_SHA": "3333333333333333333333333333333333333333",
            "FAKE_CURL_HTTP_CODE": "500",
        },
    )
    _assert_missing_script_failure(run)

    combined = f"{run.completed.stdout}\n{run.completed.stderr}".lower()
    assert run.completed.returncode != 0
    assert "rollback" in combined
    assert "git reset --hard" in combined
    assert old_sha in combined or old_sha[:7] in combined
    assert run.git_state_file.exists()
    assert run.git_state_file.read_text(encoding="utf-8").strip() == old_sha
