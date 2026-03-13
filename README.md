# 🚀 数字商品自动售卖 SaaS 平台

> 基于 **Python (uv) + Reflex + Aiogram + PostgreSQL** 的多租户 Bot 矩阵平台

## 📋 项目概述

本项目是一个完整的数字商品自动售卖 SaaS 平台，包含：

- **Telegram Bot** - C端用户自动售卖机器人（支持多Bot实例）
- **Reflex 后台** - 超级管理员、代理商、供货商的多角色管理面板
- **USDT 支付** - TRC20 链上交易监听与自动入账

## 🛠️ 技术栈

| 组件 | 技术 |
|------|------|
| Web 框架 | Reflex (Python 全栈) |
| Bot 框架 | Aiogram 3.x |
| 数据库 | PostgreSQL + SQLModel |
| 缓存/队列 | Redis |
| 支付链 | USDT TRC20 (TronGrid API) |
| 包管理 | uv |

## 📁 项目结构

```
project_root/
├── shared/              # 共享模块
│   ├── config.py       # 全局配置
│   ├── database.py     # 数据库连接
│   └── models/         # 数据模型
├── bot/                 # Telegram Bot
│   ├── handlers/       # 消息处理器
│   └── main.py         # Bot 入口
├── test_reflex/         # Reflex 后台
│   ├── pages/          # 页面
│   ├── state/          # 状态管理
│   ├── components/     # 组件
│   └── templates/      # 模板
├── services/            # 业务服务
│   └── importer.py     # 库存导入
└── docs/                # 文档
```

## 🚀 快速开始

### 1. 安装依赖

```bash
# 使用 uv 安装依赖
uv sync
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，配置数据库、Bot Token 等
```

### 3. 启动后台管理系统

```bash
uv run reflex run
```

访问 http://localhost:3000

### 4. Bot 运行说明

Bot supervisor 已集成到 Reflex 生命周期中，`uv run reflex run` 启动后会自动按数据库中启用的 Bot 配置运行。
不再单独运行 `python -m bot.main`。

## 🔐 生产部署注意

- 不要使用默认密码；`SUPER_ADMIN_PASSWORD` 必须为强密码。
- 生产环境 Bot Token 由后台 Bot 管理页面配置，不在部署脚本里输入。
- PostgreSQL (`5432`) 和 Redis (`6379`) 不应对公网开放。
- 首次登录后请立即修改管理员密码。

## 📊 功能模块

### 后台管理

- ✅ 仪表盘 - 运营数据总览
- ✅ 库存管理 - 商品导入、分类
- 🔲 Bot 管理 - 多Bot实例
- 🔲 用户管理 - CRM
- 🔲 订单管理 - 订单查询、退款
- 🔲 财务中心 - 充值记录、对账
- 🔲 代理管理 - 代理商分润
- 🔲 商家管理 - 供货商入驻

### Telegram Bot

- ✅ 基础框架 - /start、/help
- ✅ 菜单键盘 - 功能导航
- 🔲 商品浏览 - 分类展示
- 🔲 购物车 - 多选结算
- 🔲 USDT 充值 - 链上到账
- 🔲 自动发货 - 购买后即时发送

## 📝 开发计划

详见 [实施计划文档](.agent/artifacts/implementation_plan.md)

## 📄 许可证

Private - All Rights Reserved

## Runtime Backend Policy

- Application runtime is DB-only for export and push repositories.
- `EXPORT_TASK_BACKEND` and `PUSH_QUEUE_BACKEND` should remain `db` in normal environments.
- `memory` backend is reserved for explicit test injection paths.
