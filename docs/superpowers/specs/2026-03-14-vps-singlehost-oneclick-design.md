# VPS 单机一键部署设计（方案1）

## 1. 目标与边界

### 1.1 目标

在一台全新 Ubuntu 24.04 VPS（1核1G）上，以最低复杂度实现生产可运行部署：
- 一键部署（单命令）
- 可重复执行（幂等）
- 默认安全基线（避免默认弱配置与未授权访问）
- 可维护（日志、备份、升级、回滚流程明确）

### 1.2 已确认约束

- 部署模式：方案1（极简单栈）
- 主机资源：1C1G
- 网络：无域名，公网 IP 访问
- 访问模式：多人公网直接访问后台
- 并发规模：< 50
- 配置要求：部署阶段不采集 `BOT_TOKEN`
- PostgreSQL/Redis 不对公网直接暴露

### 1.3 非目标

- 不在本阶段实现蓝绿发布/双机高可用
- 不在本阶段引入 HTTPS 证书自动化（后续域名到位后增强）

## 2. 方案对比与选型

### 2.1 备选方案

1. 极简单栈（选中）：`docker compose` 单套（web + postgres + redis）
2. 单机蓝绿：单机两套 web + 反向代理切流
3. 双机主备：跨主机高可用

### 2.2 选型理由

在“简单优先 + 一键化 + 单机资源有限”前提下，方案1具备最小运维复杂度和最低出错面。虽然升级阶段存在短暂停机，但满足当前阶段快速上线目标。

## 3. 目标架构

### 3.1 服务拓扑

- `web`：Reflex 后台 + Bot supervisor（lifespan 内运行）
- `postgres`：PostgreSQL 16
- `redis`：Redis 7

三者在同一 Docker 网络中，应用通过服务名通信：
- `postgres:5432`
- `redis:6379`

### 3.2 对外暴露端口

- 暴露：`3000`（后台页面）
- 可选暴露：`8000`（若需要外部 API；不需要则不映射）
- 不暴露：`5432`、`6379`

## 4. 安全设计

### 4.1 PostgreSQL 安全边界

- 不映射宿主机 `5432`，仅容器内网访问
- 使用 `POSTGRES_DB/POSTGRES_USER/POSTGRES_PASSWORD` 初始化数据库
- 应用连接串固定走容器域名：
  - `DATABASE_URL=postgresql+asyncpg://postgres:<DB_PASSWORD>@postgres:5432/reflex`

### 4.2 Redis 安全边界

- 不映射宿主机 `6379`，仅容器内网访问
- Redis 启动参数强制启用密码：`--requirepass <REDIS_PASSWORD>`
- 应用连接串包含认证信息：
  - `REDIS_URL=redis://:<REDIS_PASSWORD>@redis:6379/0`

### 4.3 应用安全基线

- 强制设置 `SUPER_ADMIN_PASSWORD`（强密码）
- 自动生成 `SECRET_KEY`、`DB_PASSWORD`、`REDIS_PASSWORD`
- `.env` 权限设置为 `600`
- 禁止演示数据注入并默认清理历史演示数据：
  - `BOOTSTRAP_DEMO_DATA_ENABLED=0`
  - `BOOTSTRAP_PURGE_DEMO_DATA=1`

### 4.4 BOT_TOKEN 策略

- `deploy.sh` 不采集 `BOT_TOKEN`
- 运行时 bot token 来源于后台数据库 Bot 配置
- `settings.bot_token` 可为空，仅保留兼容回退能力

## 5. 一键部署流程（deploy.sh）

### 5.1 阶段 A：系统准备

- 校验 root/sudo
- 安装 Docker Engine + Compose Plugin（若缺失）
- 启用 Docker 服务

### 5.2 阶段 B：配置采集

交互输入：
- `SUPER_ADMIN_PASSWORD`（强校验）
- `TRONGRID_API_KEY`（可空）

自动生成：
- `DB_PASSWORD`
- `REDIS_PASSWORD`
- `SECRET_KEY`

不采集：
- `BOT_TOKEN`

### 5.3 阶段 C：生成 .env

关键变量：
- `DATABASE_URL=postgresql+asyncpg://postgres:${DB_PASSWORD}@postgres:5432/reflex`
- `DB_PASSWORD=${DB_PASSWORD}`
- `REDIS_PASSWORD=${REDIS_PASSWORD}`
- `REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0`
- `SUPER_ADMIN_PASSWORD=<input>`
- `SECRET_KEY=${SECRET_KEY}`
- `TRONGRID_API_KEY=<input-or-empty>`
- `EXPORT_TASK_BACKEND=db`
- `PUSH_QUEUE_BACKEND=db`
- `BOOTSTRAP_DEMO_DATA_ENABLED=0`
- `BOOTSTRAP_PURGE_DEMO_DATA=1`

并执行：`chmod 600 .env`。

### 5.4 阶段 D：构建与启动

- `docker compose build`
- `docker compose up -d`
- 健康检查：postgres、redis、web

### 5.5 阶段 E：验收输出

输出：
- 访问地址：`http://<VPS_IP>:3000`
- 常用运维命令
- 首次上线必要动作提示（后台创建 Bot、修改管理密码）

## 6. Compose 设计细节

### 6.1 postgres

- 镜像：`postgres:16-alpine`
- 环境：
  - `POSTGRES_USER=postgres`
  - `POSTGRES_PASSWORD=${DB_PASSWORD}`
  - `POSTGRES_DB=reflex`
- 数据卷：`pgdata:/var/lib/postgresql/data`
- healthcheck：`pg_isready -U postgres`

### 6.2 redis

- 镜像：`redis:7-alpine`
- command：`redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}`
- 不暴露端口
- healthcheck：`redis-cli -a ${REDIS_PASSWORD} ping`

### 6.3 web

- 构建本地 Dockerfile
- `env_file: .env`
- 端口：`3000:3000`（`8000`按需）
- 依赖：postgres/redis healthy 后启动
- 挂载：
  - `reflex_data:/app/.states`
  - `uploaded_files:/app/uploaded_files`
- 日志轮转：`max-size=10m`, `max-file=3`

## 7. 运维手册（最小集）

### 7.1 首次部署

- `sudo bash deploy.sh`
- 访问：`http://<VPS_IP>:3000`
- 在后台创建并启用实际 Bot（配置 token）

### 7.2 日常升级

- `git pull`
- `docker compose up -d --build`

### 7.3 回滚

- 切回上一稳定 commit/tag
- 重新执行：`docker compose up -d --build`

### 7.4 备份恢复

- 备份：
  - `docker compose exec -T postgres pg_dump -U postgres reflex > backup_$(date +%F).sql`
- 恢复：
  - `docker compose exec -T postgres psql -U postgres reflex < backup_xxx.sql`

## 8. 验收标准

上线验收通过需满足：
- `docker compose ps` 三服务均为 Up/healthy
- 后台可通过公网 IP 正常访问
- 登录与核心页面可用
- Redis/Postgres 不对公网直接开放
- `.env` 权限为 600
- 不存在默认演示数据回灌

## 9. 风险与后续增强

### 9.1 当前风险

- 无域名阶段为 HTTP 明文访问，不适合长期高安全场景
- 方案1升级存在短暂停机

### 9.2 后续增强

- 获得域名后增加 Caddy/Nginx + HTTPS
- 未来可升级到单机蓝绿或双机主备

## 10. 结论

在当前业务阶段与资源约束下，方案1是最匹配“简单、一键、可维护”的生产部署方案。关键落实点：
- 不采集 `BOT_TOKEN`（改由后台数据库配置）
- Postgres/Redis 仅内网访问，Redis 开启密码认证
- 统一 `deploy.sh` 完成安装、配置、启动、校验闭环
