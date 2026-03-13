# VPS 部署设计文档

## 概述

将数字商品自动售卖 SaaS 平台一键部署到全新 Ubuntu VPS，使用 Docker Compose 编排所有服务，配合一键部署脚本实现零手动配置。

## 技术栈

- **容器化**: Docker + Docker Compose
- **数据库**: PostgreSQL 16 (Docker 官方镜像)
- **缓存**: Redis 7 (Docker 官方镜像)
- **应用**: Python 3.12 + Reflex + Aiogram
- **包管理**: uv

## 架构

```
VPS (Ubuntu)
├── Docker Engine
└── docker compose
    ├── postgres:16-alpine   (port 5432 内部, volume: pgdata)
    ├── redis:7-alpine       (port 6379 内部)
    ├── web                  (Reflex 后台, port 3000+8000 → host)
    └── bot                  (Telegram Bot, 无对外端口)
```

所有服务通过 Docker 内部网络通信。仅 web 服务暴露端口到宿主机。

## 需要创建的文件

### 1. Dockerfile

多阶段构建，减小最终镜像体积：

**Stage 1 (builder):**
- 基于 `python:3.12-slim`
- 安装 uv
- `uv sync` 安装所有 Python 依赖
- `reflex init` + `reflex export` 预编译前端静态文件

**Stage 2 (runtime):**
- 基于 `python:3.12-slim`
- 仅复制虚拟环境 + 源码 + 编译好的前端资源
- 不包含构建工具，镜像更精简

`web` 和 `bot` 服务共用同一镜像，通过不同的启动命令区分：
- `web`: `reflex run --env prod`
- `bot`: `python -m bot.main`

### 2. docker-compose.yml

四个服务：

**postgres:**
- `postgres:16-alpine` 镜像
- 环境变量: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` 从 `.env` 读取
- 数据持久化: named volume `pgdata` 映射到 `/var/lib/postgresql/data`
- healthcheck: `pg_isready` 确保数据库就绪
- `restart: unless-stopped`

**redis:**
- `redis:7-alpine` 镜像
- `restart: unless-stopped`

**web:**
- 本地构建的应用镜像
- 命令: `reflex run --env prod`
- 端口映射: `3000:3000`, `8000:8000`
- `env_file: .env`
- `depends_on` postgres (healthy) + redis (started)
- `restart: unless-stopped`

**bot:**
- 同一应用镜像
- 命令: `python -m bot.main`
- `env_file: .env`
- `depends_on` postgres (healthy) + redis (started)
- `restart: unless-stopped`

**volumes:**
- `pgdata`: PostgreSQL 数据持久化

### 3. deploy.sh (一键部署脚本)

执行流程：

1. **权限检查** — 确认以 root 或 sudo 运行
2. **安装 Docker** — 检测是否已安装，未安装则通过官方脚本安装 Docker Engine + Compose plugin
3. **配置生成** — 交互式询问或自动生成：
   - `BOT_TOKEN`: 用户输入
   - `DB_PASSWORD`: 自动生成 32 位随机密码
   - `SECRET_KEY`: 自动生成 64 位随机密钥
   - `TRONGRID_API_KEY`: 可选输入
4. **生成 .env** — `DATABASE_URL` 指向 `postgres` 容器（`postgresql+asyncpg://postgres:<password>@postgres:5432/reflex`），`REDIS_URL` 指向 `redis` 容器
5. **构建并启动** — `docker compose build && docker compose up -d`
6. **等待就绪** — 轮询 postgres 健康状态
7. **输出结果** — 打印访问地址和常用运维命令

**安全措施：**
- DB_PASSWORD 和 SECRET_KEY 自动生成随机值
- `.env` 文件权限设为 600
- 不使用任何默认密码

### 4. .dockerignore

排除不需要的文件：`.git`, `.venv`, `__pycache__`, `.env`, `*.zip`, `temp_decompile/`, `.web/`, `.states/`, `tests/` 等。

## 环境变量管理

`.env` 文件中的关键变量在 Docker 环境下的值：

| 变量 | 值 |
|------|-----|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:<password>@postgres:5432/reflex` |
| `REDIS_URL` | `redis://redis:6379/0` |
| `DEBUG` | `false` |
| `BOT_TOKEN` | 用户提供 |
| `SECRET_KEY` | 自动生成 |

注意：容器间通过服务名（`postgres`, `redis`）通信，而非 `localhost`。

## 数据持久化与备份

- PostgreSQL 数据存储在 Docker named volume `pgdata` 中
- 容器重建不影响数据
- 备份命令: `docker compose exec postgres pg_dump -U postgres reflex > backup.sql`
- 恢复命令: `docker compose exec -T postgres psql -U postgres reflex < backup.sql`

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
