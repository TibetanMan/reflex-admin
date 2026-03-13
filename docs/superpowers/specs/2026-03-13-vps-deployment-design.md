# VPS 部署设计文档

## 概述

将数字商品自动售卖 SaaS 平台一键部署到全新 Ubuntu VPS，使用 Docker Compose 编排所有服务，配合一键部署脚本实现零手动配置。

## 技术栈

- **容器化**: Docker + Docker Compose
- **数据库**: PostgreSQL 16 (Docker 官方镜像)
- **缓存**: Redis 7 (Docker 官方镜像)
- **应用**: Python 3.12 + Node.js 20 + Reflex + Aiogram
- **包管理**: uv

## 架构

```
VPS (Ubuntu)
├── Docker Engine
└── docker compose
    ├── postgres:16-alpine   (port 5432 内部, volume: pgdata)
    ├── redis:7-alpine       (port 6379 内部, healthcheck: redis-cli ping)
    └── web                  (Reflex 后台 + Bot lifespan, port 3000+8000 → host)
```

**重要：Bot 不是独立进程。** Telegram Bot supervisor 作为 Reflex lifespan task 运行（见 `test_reflex/test_reflex.py` 中的 `_register_runtime_lifespan_tasks`）。`python -m bot.main` 已被移除并会抛出 `RuntimeError`。因此只需 **三个** Docker 服务：postgres、redis、web。

所有服务通过 Docker 内部网络通信。仅 web 服务暴露端口到宿主机。

## 需要创建的文件

### 1. Dockerfile

多阶段构建：

**Stage 1 (builder):**
- 基于 `python:3.12-slim`
- 安装 uv + Node.js 20（Reflex 运行时需要 Node.js 来服务前端）
- `uv sync` 安装所有 Python 依赖
- `reflex init` 初始化前端项目结构（生成 `.web/` 目录）

**Stage 2 (runtime):**
- 基于 `python:3.12-slim`
- 安装 Node.js 20 运行时（Reflex `--env prod` 仍需要 Node.js 运行 Next.js 服务）
- 复制虚拟环境 + 源码 + `.web/` 目录
- 安装前端依赖（`cd .web && npm install`）

**注意：** Reflex 0.8.x 在 `--env prod` 模式下仍需 Node.js 运行 Next.js production server，因此 runtime 阶段必须包含 Node.js。

启动命令：`reflex run --env prod`（同时运行 Reflex 后台 + Bot lifespan task）

### 2. docker-compose.yml

三个服务：

**postgres:**
- `postgres:16-alpine` 镜像
- 环境变量: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` 从 `.env` 读取
- 数据持久化: named volume `pgdata` 映射到 `/var/lib/postgresql/data`
- healthcheck: `pg_isready -U postgres` 确保数据库就绪
- `restart: unless-stopped`

**redis:**
- `redis:7-alpine` 镜像
- healthcheck: `redis-cli ping`
- `restart: unless-stopped`

**web:**
- 本地构建的应用镜像
- 命令: `reflex run --env prod`
- 端口映射: `3000:3000`, `8000:8000`
- `env_file: .env`
- `depends_on` postgres (service_healthy) + redis (service_healthy)
- volume 挂载: `reflex_data:/app/.states`（Reflex 内部状态持久化）
- healthcheck: `curl -f http://localhost:8000/ping || exit 1`（如有 health endpoint）
- `restart: unless-stopped`
- 日志轮转: `logging: { driver: json-file, options: { max-size: "10m", max-file: "3" } }`

**volumes:**
- `pgdata`: PostgreSQL 数据持久化
- `reflex_data`: Reflex 内部状态（SQLite）持久化

### 3. deploy.sh (一键部署脚本)

执行流程：

1. **权限检查** — 确认以 root 或 sudo 运行
2. **安装 Docker** — 检测是否已安装，未安装则通过官方脚本安装 Docker Engine + Compose plugin
3. **配置生成** — 交互式询问或自动生成：
   - `BOT_TOKEN`: 用户输入（校验格式 `[0-9]+:[A-Za-z0-9_-]+`）
   - `DB_PASSWORD`: 自动生成 32 位随机密码
   - `SECRET_KEY`: 自动生成 64 位随机密钥
   - `TRONGRID_API_KEY`: 可选输入
4. **生成 .env** — `DATABASE_URL` 指向 `postgres` 容器，`REDIS_URL` 指向 `redis` 容器
5. **构建并启动** — `docker compose build && docker compose up -d`
6. **等待就绪** — 轮询 postgres 健康状态
7. **输出结果** — 打印访问地址和常用运维命令

**安全措施：**
- DB_PASSWORD 和 SECRET_KEY 自动生成随机值
- `.env` 文件权限设为 600
- 不使用任何默认密码

### 4. .dockerignore

排除不需要的文件：`.git`, `.venv`, `__pycache__`, `.env`, `*.zip`, `temp_decompile/`, `.web/`, `.states/`, `tests/`, `.claude/`, `.agent/` 等。

## 环境变量管理

`.env` 文件中的关键变量在 Docker 环境下的值：

| 变量 | 值 |
|------|-----|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:<password>@postgres:5432/reflex` |
| `REDIS_URL` | `redis://redis:6379/0` |
| `DEBUG` | `false` |
| `BOT_TOKEN` | 用户提供 |
| `SECRET_KEY` | 自动生成 |

注意：
- 容器间通过服务名（`postgres`, `redis`）通信，而非 `localhost`
- `psycopg2-binary` 是必需运行时依赖（同步引擎通过 `replace("+asyncpg", "")` 派生同步 URL）
- Dockerfile 中无需额外安装 `libpq-dev`，因为 `psycopg2-binary` 自带 `libpq`

## Reflex 内部状态管理

Reflex 维护自己的内部状态数据库（默认 SQLite）。在 Docker 环境中：
- 挂载 volume `reflex_data` 到 `/app/.states`，确保容器重启不丢失 Reflex 状态
- 如果后续需要，可在 `rxconfig.py` 中配置 `db_url` 指向 PostgreSQL

## 数据持久化与备份

- PostgreSQL 数据存储在 Docker named volume `pgdata` 中
- 容器重建不影响数据
- 备份命令: `docker compose exec postgres pg_dump -U postgres reflex > backup.sql`
- 恢复命令: `docker compose exec -T postgres psql -U postgres reflex < backup.sql`

## HTTPS / TLS（后续增强）

当前设计使用 HTTP + IP 直接访问。后续如需域名 + HTTPS：
- 在 `docker-compose.yml` 中添加 Caddy 服务作为反向代理
- Caddy 自动申请 Let's Encrypt 证书
- 将 web 服务的端口映射改为仅内部访问
- 对于处理 USDT 支付的生产环境，强烈建议配置 HTTPS

## 部署后运维

常用命令：
- `docker compose logs -f` — 查看所有服务日志
- `docker compose logs -f web` — 查看 Web 日志
- `docker compose restart web` — 重启 Web 服务
- `docker compose down` — 停止所有服务
- `docker compose up -d --build` — 重新构建并启动（代码更新后）

## 用户操作流程

1. 在本地编辑配置（或让脚本交互式生成）
2. `rsync` 或 `scp` 将项目文件传到 VPS
3. SSH 登录 VPS
4. `cd /path/to/project && bash deploy.sh`
5. 按提示输入 BOT_TOKEN
6. 等待部署完成
7. 访问 `http://VPS_IP:3000`
