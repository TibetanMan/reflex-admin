from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_deploy_script_does_not_prompt_bot_token_and_writes_security_env():
    source = _read("deploy.sh")
    assert "Enter your Telegram BOT_TOKEN" not in source
    assert "BOT_TOKEN=${BOT_TOKEN}" not in source
    assert "SUPER_ADMIN_PASSWORD" in source
    assert "REDIS_PASSWORD" in source
    assert "REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0" in source
    assert "BOOTSTRAP_DEMO_DATA_ENABLED=0" in source
    assert "BOOTSTRAP_PURGE_DEMO_DATA=1" in source


def test_compose_keeps_postgres_redis_internal_and_redis_requires_password():
    source = _read("docker-compose.yml")
    assert "postgres:" in source
    assert "redis:" in source
    assert "redis-server --appendonly yes --requirepass ${REDIS_PASSWORD" in source
    assert 'redis-cli -a ${REDIS_PASSWORD} ping' in source
    postgres_block = source.split("postgres:")[1].split("redis:")[0]
    redis_block = source.split("redis:")[1].split("web:")[0]
    assert "ports:" not in postgres_block
    assert "ports:" not in redis_block


def test_env_example_and_readme_match_new_deploy_policy():
    env_source = _read(".env.example")
    readme = _read("README.md")
    assert "REDIS_PASSWORD" in env_source
    assert "REDIS_URL=redis://:" in env_source
    assert "SUPER_ADMIN_PASSWORD" in env_source
    assert "admin123" not in readme
