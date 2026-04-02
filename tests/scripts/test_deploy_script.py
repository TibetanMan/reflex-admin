from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_SCRIPT = REPO_ROOT / "deploy.sh"


def test_deploy_script_reuses_existing_service_credentials() -> None:
    source = SOURCE_SCRIPT.read_text(encoding="utf-8")

    assert "source .env" in source
    assert 'DB_PASSWORD="${DB_PASSWORD:-$(openssl rand -base64 24 | tr -d \'/+=\' | head -c 32)}"' in source
    assert 'REDIS_PASSWORD="${REDIS_PASSWORD:-$(openssl rand -base64 24 | tr -d \'/+=\' | head -c 32)}"' in source
    assert 'SECRET_KEY="${SECRET_KEY:-$(openssl rand -base64 48 | tr -d \'/+=\' | head -c 64)}"' in source