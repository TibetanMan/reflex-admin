# VPS 单机一键部署（方案1）Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Ubuntu 24.04 单机（1C1G）上实现简单、可重复的一键部署，满足“不采集 BOT_TOKEN、PostgreSQL/Redis 不公网暴露、Redis 防未授权访问”的生产基线。

**Architecture:** 采用单套 Docker Compose（三服务：web/postgres/redis）。`deploy.sh` 负责系统准备、配置采集、`.env` 生成、构建启动与健康检查。Bot token 不在部署期输入，运行时由后台数据库 Bot 配置驱动；Redis 使用密码认证且仅内网访问。

**Tech Stack:** Docker, Docker Compose, Bash, Python (pytest), Reflex, PostgreSQL 16, Redis 7

Spec: `docs/superpowers/specs/2026-03-14-vps-singlehost-oneclick-design.md`

---

## File Structure

- Modify: `docker-compose.yml`
  - 定义三服务部署拓扑；强制 PostgreSQL/Redis 仅内网访问；Redis 加 `requirepass`；健康检查可认证。
- Modify: `deploy.sh`
  - 一键部署入口；移除 `BOT_TOKEN` 采集；新增 `SUPER_ADMIN_PASSWORD` 强校验；生成 `REDIS_PASSWORD`；写入安全 `.env`。
- Modify: `.env.example`
  - 同步新的部署变量与说明（`REDIS_PASSWORD`、带认证的 `REDIS_URL`、`BOT_TOKEN` 非部署期必填）。
- Modify: `README.md`
  - 修正部署说明与默认账号误导内容，避免 `admin123` 这类过时信息。
- Create: `tests/test_vps_deploy_contract.py`
  - 通过文本契约测试锁住部署安全约束，防回归（不需要真实起容器）。

---

## Chunk 1: Contract Tests First (TDD)

### Task 1: 新增部署契约测试（先失败）

**Files:**
- Create: `tests/test_vps_deploy_contract.py`

- [ ] **Step 1: 写失败测试 - deploy.sh 不采集 BOT_TOKEN 且写入安全变量**

```python
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
```

- [ ] **Step 2: 写失败测试 - compose 必须禁止 Postgres/Redis 对外暴露并开启 Redis 认证**

```python
def test_compose_keeps_postgres_redis_internal_and_redis_requires_password():
    source = _read("docker-compose.yml")
    assert "postgres:" in source
    assert "redis:" in source
    assert "redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}" in source
    assert 'redis-cli -a ${REDIS_PASSWORD} ping' in source
    # postgres/redis 服务块中不应出现 ports 映射
    postgres_block = source.split("postgres:")[1].split("redis:")[0]
    redis_block = source.split("redis:")[1].split("web:")[0]
    assert "ports:" not in postgres_block
    assert "ports:" not in redis_block
```

- [ ] **Step 3: 写失败测试 - .env.example 与 README 文案一致**

```python
def test_env_example_and_readme_match_new_deploy_policy():
    env_source = _read(".env.example")
    readme = _read("README.md")
    assert "REDIS_PASSWORD" in env_source
    assert "REDIS_URL=redis://:" in env_source
    assert "SUPER_ADMIN_PASSWORD" in env_source
    assert "admin123" not in readme
```

- [ ] **Step 4: 运行测试确认失败**

Run: `uv run pytest tests/test_vps_deploy_contract.py -v`  
Expected: FAIL（当前文件仍包含旧 BOT_TOKEN 交互、Redis 未鉴权、README 默认账号文案等）

- [ ] **Step 5: Commit（只提交失败测试）**

```bash
git add tests/test_vps_deploy_contract.py
git commit -m "test: add VPS deploy security contract tests"
```

---

## Chunk 2: Compose + Deploy Script Implementation

### Task 2: 修改 docker-compose.yml 满足数据库/Redis 内网与鉴权要求

**Files:**
- Modify: `docker-compose.yml`
- Test: `tests/test_vps_deploy_contract.py`

- [ ] **Step 1: 修改 Redis 启动命令与健康检查**

```yaml
redis:
  image: redis:7-alpine
  command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD:?REDIS_PASSWORD must be set in .env}
  healthcheck:
    test: ["CMD-SHELL", "redis-cli -a ${REDIS_PASSWORD} ping | grep PONG"]
```

- [ ] **Step 2: 确认 postgres/redis 均无 ports 暴露**

```yaml
postgres:
  # no ports
redis:
  # no ports
```

- [ ] **Step 3: 保持 web 对外映射（3000，8000按当前需求保留）**

```yaml
web:
  ports:
    - "3000:3000"
    - "8000:8000"
```

- [ ] **Step 4: 跑契约测试局部验证**

Run: `uv run pytest tests/test_vps_deploy_contract.py::test_compose_keeps_postgres_redis_internal_and_redis_requires_password -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add docker-compose.yml
git commit -m "feat: harden compose network boundaries and redis auth"
```

### Task 3: 修改 deploy.sh，移除 BOT_TOKEN 交互并加入强密码/Redis 密码

**Files:**
- Modify: `deploy.sh`
- Test: `tests/test_vps_deploy_contract.py`

- [ ] **Step 1: 删除 BOT_TOKEN 采集与格式校验**

```bash
# remove:
# read -rp "Enter your Telegram BOT_TOKEN: " BOT_TOKEN
# BOT_TOKEN=${BOT_TOKEN}
```

- [ ] **Step 2: 新增 SUPER_ADMIN_PASSWORD 交互与强度校验函数**

```bash
is_strong_password() {
  local p="$1"
  [[ ${#p} -ge 12 ]] || return 1
  [[ "$p" =~ [a-z] ]] || return 1
  [[ "$p" =~ [A-Z] ]] || return 1
  [[ "$p" =~ [0-9] ]] || return 1
  [[ "$p" =~ [^A-Za-z0-9] ]] || return 1
}
```

- [ ] **Step 3: 新增 REDIS_PASSWORD 生成与 .env 输出**

```bash
REDIS_PASSWORD=$(openssl rand -base64 24 | tr -d '/+=' | head -c 32)
...
REDIS_PASSWORD=${REDIS_PASSWORD}
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
SUPER_ADMIN_PASSWORD=${SUPER_ADMIN_PASSWORD}
BOOTSTRAP_DEMO_DATA_ENABLED=0
BOOTSTRAP_PURGE_DEMO_DATA=1
```

- [ ] **Step 4: 修正健康检查与结果输出文案**

```bash
docker compose exec -T redis sh -lc 'redis-cli -a "$REDIS_PASSWORD" ping'
```

并删除“Default login admin/admin123”输出。

- [ ] **Step 5: 跑契约测试局部验证**

Run: `uv run pytest tests/test_vps_deploy_contract.py::test_deploy_script_does_not_prompt_bot_token_and_writes_security_env -v`  
Expected: PASS

- [ ] **Step 6: Bash 语法检查**

Run: `bash -n deploy.sh`  
Expected: 无输出且 exit code 0

- [ ] **Step 7: Commit**

```bash
git add deploy.sh
git commit -m "feat: one-click deploy without bot token prompt and with redis/super-admin security"
```

---

## Chunk 3: Docs Alignment + End-to-End Verification

### Task 4: 更新 .env.example 与 README，避免误导

**Files:**
- Modify: `.env.example`
- Modify: `README.md`
- Test: `tests/test_vps_deploy_contract.py`

- [ ] **Step 1: 更新 .env.example**

新增/调整：
- `REDIS_PASSWORD=...`
- `REDIS_URL=redis://:<password>@...`
- `SUPER_ADMIN_PASSWORD=...`（强密码提示）
- 说明 `BOT_TOKEN` 不由 deploy 阶段采集（由后台 Bot 配置）

- [ ] **Step 2: 更新 README 部署说明**

- 删除 `admin/admin123` 测试账号段落
- 增加生产部署注意：
  - 首次登录后立即改密
  - Bot token 在后台配置
  - 5432/6379 不开放公网

- [ ] **Step 3: 跑契约测试**

Run: `uv run pytest tests/test_vps_deploy_contract.py -v`  
Expected: 全部 PASS

- [ ] **Step 4: Commit**

```bash
git add .env.example README.md tests/test_vps_deploy_contract.py
git commit -m "docs: align env/readme with one-click production deployment policy"
```

### Task 5: 最终集成验证（不使用 pytest -q）

**Files:**
- Verify only

- [ ] **Step 1: 静态校验 compose**

Run: `docker compose config`  
Expected: YAML 展开成功，无 schema 错误

- [ ] **Step 2: Python 语法校验关键文件**

Run: `uv run python -m py_compile shared/bootstrap.py test_reflex/test_reflex.py services/bot_service.py`  
Expected: PASS

- [ ] **Step 3: 回归相关测试**

Run:
`uv run pytest tests/test_bootstrap_super_admin.py tests/services/test_dashboard_service.py tests/api/test_phase2_http_api_bridge.py tests/test_vps_deploy_contract.py -v`

Expected: PASS（允许已有已知 warning，但无失败）

- [ ] **Step 4: Commit（若验证阶段有修正）**

```bash
git add -A
git commit -m "chore: finalize VPS one-click deployment validation"
```

仅当验证修正产生代码改动时提交，否则跳过此步。

---

## Execution Notes

- 全流程禁止使用 `pytest -q`，统一使用 `-v`。
- 如在执行中发现与当前 dirty 工作区冲突，优先只暂存本计划涉及文件，避免夹带无关变更。
- 若 VPS 首次部署后发现 8000 端口无需公网访问，可在后续小改中移除 web 的 `8000:8000` 映射（不影响核心方案）。

