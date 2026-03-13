# Test-Reflex 数据库对接准备文档（API + ORM + 权限）

> 日期：2026-02-16  
> 目标：基于当前项目所有页面与状态逻辑，给出可直接落地的 API 设计与 ORM 模型清单，用于后续 PostgreSQL 对接。  
> 范围：`test_reflex/pages/*`、`test_reflex/state/*`、`shared/models/*`、`services/*`、`bot/handlers/*`。

---

## 1. 页面/模块全量盘点

| 模块 | 路由/入口 | 当前能力 | 对接重点 |
|---|---|---|---|
| 登录 | `/login` | 账号密码登录、记住我、错误提示 | 认证、会话、RBAC |
| 仪表盘 | `/` | 销售/订单/用户/库存统计、最近订单/充值 | 聚合查询、趋势统计 |
| Bot 管理 | `/bots` | Bot 列表、创建、编辑、删除、启停 | BotInstance、Owner 归属、USDT 地址 |
| 库存管理 | `/inventory` | 库筛选、导入、预览、价格调整、启停、删除 | 库维度模型、导入任务、行级库存 |
| 订单管理 | `/orders` | 订单筛选、详情、退款、导出 | 订单主表/明细、退款审计、导出任务 |
| 用户管理 | `/users` | 用户筛选、封禁、余额调整、明细、导出、活动抽屉 | 用户多 Bot 来源、资金流水、审计 |
| 财务中心 | `/finance` | 充值记录、手动充值、钱包列表 | Deposit、Wallet、手工入账流水 |
| 消息推送 | `/push` | 审核队列、推送编排、定时、队列状态 | Push 审核表、任务表、审计表 |
| 代理管理 | `/agents` | 代理 CRUD、启停、认证、分润配置 | Agent + AdminUser + Bot 绑定 |
| 商家管理 | `/merchants` | 商家 CRUD、启停、认证、推荐、费率 | Merchant、结算与评分字段 |
| 系统设置 | `/settings` | 默认 USDT、USDT/BINS API、Telegram 推送配置 | 系统配置持久化 |
| 个人资料 | `/profile` | 个人资料展示 | AdminUser 扩展信息 |
| Bot 侧菜单 | `bot/handlers/*` | /start/help、分类、充值、余额、购物车、订单记录 | C 端查询/下单/充值 API |

---

## 2. 统一规范（必须先统一）

### 2.1 API 规范

- 前缀：`/api/v1`
- 认证：后台采用 `Bearer JWT`（Access + Refresh）；Bot 侧采用 `bot_token + telegram user proof`。
- 响应统一：
  - 成功：`{ "code": 0, "message": "ok", "data": ... }`
  - 失败：`{ "code": <业务码>, "message": "...", "errors": [...] }`
- 分页统一：`page`、`page_size`、`total`、`items`
- 时间统一：ISO8601，数据库存 `TIMESTAMP WITH TIME ZONE`
- 金额统一：数据库使用 `NUMERIC(18,2)`，禁止 `float` 持久化金额

### 2.2 命名与状态枚举统一

- Bot 状态：`active | inactive | pending | error`
- 订单状态：`pending | paid | completed | refunded | cancelled`
- 充值状态：`pending | confirming | completed | failed | expired`
- 推送状态：`pending_review | approved | queued | processing | sent | failed | cancelled`
- 用户状态：`active | banned`
- 统一字段：`created_at`、`updated_at`、`created_by`、`updated_by`、`deleted_at(软删)`

### 2.3 权限与数据域

- 角色：`super_admin`、`agent`、`merchant`
- 校验层次：
  - 页面权限（前端显示）
  - API 角色权限（后端硬校验）
  - 数据域权限（Row-Level）
- 数据域规则：
  - `super_admin`：全量
  - `agent`：仅可访问 `owner_agent_id = self.agent_id` 相关 Bot、用户、订单、充值、推送
  - `merchant`：仅可访问 `supplier_id = self.merchant_id` 相关库存与销售

---

## 3. RBAC 权限矩阵（按模块）

| 模块 | super_admin | agent | merchant |
|---|---:|---:|---:|
| Dashboard 查看 | ✅ | ✅(仅本域) | ✅(仅本域) |
| Bot 列表/编辑/启停 | ✅ | ✅(仅本人 Bot) | ❌ |
| Bot 删除 | ✅ | ❌（建议） | ❌ |
| 库存导入/改价/启停/删除 | ✅ | ✅(仅本人域) | ✅(仅本人域) |
| 订单查看 | ✅ | ✅(仅本人域) | ✅(仅本人商品相关) |
| 订单退款 | ✅ | ✅(仅本人域，需审计) | ❌ |
| 用户查看 | ✅ | ✅(仅本人域) | ❌ |
| 用户封禁 | ✅ | ❌（建议） | ❌ |
| 余额调整 | ✅ | ✅(仅本人域，强审计) | ❌ |
| 财务充值记录查看 | ✅ | ✅(仅本人域) | ❌ |
| 手动充值 | ✅ | ✅(仅本人域) | ❌ |
| 推送页访问 | ✅ | ❌ | ❌ |
| 推送审核与创建 | ✅ | ❌ | ❌ |
| 代理管理 | ✅ | ❌ | ❌ |
| 商家管理 | ✅ | ❌ | ❌ |
| 系统设置 | ✅ | ❌ | ❌ |
| 个人资料 | ✅ | ✅ | ✅ |

---

## 4. ORM 模型现状与补全方案

## 4.1 已有模型（可复用）

- `AdminUser`
- `Agent`
- `Merchant`
- `BotInstance`
- `User`
- `Category`
- `ProductItem`
- `Order` / `OrderItem`
- `Deposit`
- `WalletAddress`
- `BinInfo`
- `CartItem`
- `PushMessageTask` / `PushMessageAuditLog`

## 4.2 必补模型（前端功能需要，当前缺失）

### A. 库维度模型（支撑库存页）

1. `InventoryLibrary`
- 作用：库存页显示的是“库”，不是单条 `ProductItem`
- 关键字段：
  - `id`, `name`, `merchant_id`, `category_id`
  - `unit_price`, `pick_price`
  - `status(active/inactive)`
  - `total_count`, `sold_count`, `remaining_count`
  - `created_at`, `updated_at`

2. `InventoryImportTask`
- 作用：记录导入过程、进度、结果、文件
- 关键字段：
  - `id`, `library_id`, `operator_id`
  - `source_filename`, `delimiter`, `push_ad_enabled`
  - `total`, `success`, `duplicate`, `invalid`
  - `status(pending/processing/completed/failed)`
  - `started_at`, `finished_at`

3. `InventoryImportLineError`（可选）
- 作用：导入失败行追踪

### B. 用户多来源与资金审计（支撑用户页）

4. `UserBotSource`
- 作用：当前页面支持一个用户多个来源 Bot，`User.from_bot_id` 不够
- 关键字段：
  - `id`, `user_id`, `bot_id`, `is_primary`, `bound_at`

5. `BalanceLedger`
- 作用：余额加减必须可追溯，不可只改 `user.balance`
- 关键字段：
  - `id`, `user_id`, `bot_id`, `action(credit/debit/refund/manual)`
  - `amount`, `before_balance`, `after_balance`
  - `operator_id`, `remark`, `request_id`
  - `created_at`

### C. 导出任务（支撑订单/用户导出）

6. `ExportTask`
- 作用：统一订单导出、用户导出
- 关键字段：
  - `id`, `type(order/user)`, `operator_id`
  - `filters_json`, `status`
  - `progress`, `total_records`, `processed_records`
  - `file_path`, `file_name`, `error_message`
  - `created_at`, `finished_at`

### D. 推送审核（支撑 push 审核区）

7. `PushReviewTask`
- 作用：当前审核任务只在内存服务，需落库
- 关键字段：
  - `id`, `inventory_library_id`, `merchant_id`
  - `status(pending_review/approved/rejected)`
  - `source`, `created_at`, `reviewed_at`, `reviewed_by`

### E. 系统设置持久化（支撑 settings 页）

8. `SystemSetting`
- 作用：默认 USDT、API 地址、超时、Telegram 推送配置统一持久化
- 关键字段：
  - `id`, `key(unique)`, `value_json`, `updated_by`, `updated_at`

9. `ApiCredential`（可选）
- 作用：API Key/Token 脱敏与轮换（USDT/BINS）

### F. 安全审计（强烈建议）

10. `AdminAuditLog`
- 作用：关键操作留痕（退款、余额变更、封禁、配置变更、推送创建）

## 4.3 现有模型建议修正

- `Order.bot_id`、`Deposit.bot_id`、`WalletAddress.bot_id` 建议改为外键
- 金额类字段从 `float` 迁移为 `NUMERIC(18,2)`
- 为高频查询补索引：
  - `orders(created_at,status,bot_id,user_id)`
  - `deposits(created_at,status,bot_id,user_id)`
  - `product_items(status,category_id,supplier_id,created_at)`
  - `push_message_tasks(status,created_at,scheduled_publish_at)`

---

## 5. API 设计（按页面功能）

## 5.1 认证与会话（登录页/全局）

1. `POST /api/v1/auth/login`
- 权限：公开
- 请求：`username`, `password`, `remember_me`
- 响应：`access_token`, `refresh_token`, `user(role,permissions)`

2. `POST /api/v1/auth/logout`
- 权限：登录用户

3. `GET /api/v1/auth/me`
- 权限：登录用户
- 用途：刷新 navbar/sidebar 用户信息与权限

4. `POST /api/v1/auth/refresh`
- 权限：公开（持 refresh token）

## 5.2 Dashboard（仪表盘）

1. `GET /api/v1/dashboard/summary`
- 返回：`today_sales`, `today_orders`, `new_users`, `total_stock`, `trends`

2. `GET /api/v1/dashboard/recent-orders?limit=`

3. `GET /api/v1/dashboard/recent-deposits?limit=`

4. `GET /api/v1/dashboard/top-categories?limit=`

5. `GET /api/v1/dashboard/bot-status?limit=`

## 5.3 Bot 管理（/bots）

1. `GET /api/v1/bots`
- 过滤：`search`, `status`, `owner`, `page`, `page_size`
- 权限：`super_admin` 全量，`agent` 仅本人

2. `POST /api/v1/bots`
- 权限：`super_admin` / `agent(仅创建本人 bot)`
- 字段：`name`, `token`, `owner_agent_id?`, `is_platform_bot`, `usdt_address`, `welcome_message`

3. `GET /api/v1/bots/{id}`
4. `PATCH /api/v1/bots/{id}`
5. `PATCH /api/v1/bots/{id}/status`
6. `DELETE /api/v1/bots/{id}`（建议仅 `super_admin`）

## 5.4 库存管理（/inventory）

1. `GET /api/v1/inventory/libraries`
- 过滤：`search`, `merchant_id`, `status`, `sort`, `page`, `page_size`

2. `POST /api/v1/inventory/libraries/import`
- `multipart/form-data`
- 参数：`name`, `merchant_id`, `category_id`, `unit_price`, `pick_price`, `delimiter`, `push_ad`
- 结果：导入任务 `task_id`

3. `GET /api/v1/inventory/import-tasks/{task_id}`
- 返回进度、统计、错误摘要

4. `PATCH /api/v1/inventory/libraries/{id}/price`
- 参数：`unit_price`, `pick_price`

5. `PATCH /api/v1/inventory/libraries/{id}/status`
6. `DELETE /api/v1/inventory/libraries/{id}`

7. `GET /api/v1/inventory/libraries/{id}/items`
- 查看库内行级商品（用于排障/审计）

## 5.5 订单管理（/orders）

1. `GET /api/v1/orders`
- 过滤：`search`, `status`, `bot_id`, `sort`, `page`, `page_size`

2. `GET /api/v1/orders/{id}`
- 返回：订单头 + 明细（含商品名/分类/商家快照）

3. `POST /api/v1/orders/{id}/refund`
- 权限：`super_admin` / `agent(本域)`
- 请求：`reason`
- 要求：事务内完成订单状态变更 + 余额回滚 + 资金流水

4. `POST /api/v1/orders/{id}/refresh-status`

5. `POST /api/v1/orders/exports`
- 请求：`bot_name`, `date_from`, `date_to`
- 返回：`export_task_id`

6. `GET /api/v1/exports/{task_id}`
7. `GET /api/v1/exports/{task_id}/download`

## 5.6 用户管理（/users）

1. `GET /api/v1/users`
- 过滤：`search`, `status`, `bot_id`, `page`, `page_size`

2. `GET /api/v1/users/{id}`
- 返回：基础信息 + 多来源 Bot + 统计

3. `PATCH /api/v1/users/{id}/status`
- 动作：`ban/unban`

4. `POST /api/v1/users/{id}/balance-adjustments`
- 请求：`action(credit/debit)`, `amount`, `remark`, `source_bot_id`, `request_id`
- 要求：幂等（`request_id` 唯一）

5. `GET /api/v1/users/{id}/deposit-records`
6. `GET /api/v1/users/{id}/purchase-records`

7. `POST /api/v1/users/exports`
8. `GET /api/v1/exports/{task_id}`
9. `GET /api/v1/exports/{task_id}/download`

## 5.7 财务中心（/finance）

1. `GET /api/v1/finance/deposits`
- 过滤：`search`, `status`, `method`, `page`, `page_size`

2. `POST /api/v1/finance/deposits/manual`
- 请求：`user_identifier`, `amount`, `remark`, `bot_id`
- 行为：创建 `Deposit(method=manual)` + 写 `BalanceLedger` + 更新 `User.balance`

3. `GET /api/v1/finance/wallets`
4. `GET /api/v1/finance/wallets/{id}`

## 5.8 推送中心（/push）

1. `GET /api/v1/push/reviews`
- 权限：`super_admin`

2. `POST /api/v1/push/reviews/{id}/approve`
- 权限：`super_admin`

3. `POST /api/v1/push/campaigns`
- 权限：`super_admin`
- 请求：`inventory_ids`, `bot_ids`, `is_markdown`, `content`, `scheduled_publish_at`

4. `GET /api/v1/push/campaigns`
- 支持分页

5. `POST /api/v1/push/campaigns/{id}/cancel`

6. `POST /api/v1/push/queue/poll`（可选，建议内部 job 替代）

## 5.9 代理管理（/agents）

1. `GET /api/v1/agents`
2. `POST /api/v1/agents`
- 同时创建：`AdminUser(role=agent)` + `Agent` + 可选 `BotInstance`

3. `GET /api/v1/agents/{id}`
4. `PATCH /api/v1/agents/{id}`
5. `PATCH /api/v1/agents/{id}/status`

## 5.10 商家管理（/merchants）

1. `GET /api/v1/merchants`
2. `POST /api/v1/merchants`
- 同时创建：`AdminUser(role=merchant)` + `Merchant`

3. `GET /api/v1/merchants/{id}`
4. `PATCH /api/v1/merchants/{id}`
5. `PATCH /api/v1/merchants/{id}/status`
6. `PATCH /api/v1/merchants/{id}/featured`
7. `PATCH /api/v1/merchants/{id}/verified`

## 5.11 系统设置（/settings）

1. `GET /api/v1/settings`
2. `PUT /api/v1/settings/default-usdt-address`（二次确认 token）
3. `PUT /api/v1/settings/usdt-query-api`
4. `PUT /api/v1/settings/bins-query-api`
5. `PUT /api/v1/settings/telegram-push`

## 5.12 个人资料（/profile）

1. `GET /api/v1/profile`
2. `PATCH /api/v1/profile`
3. `PATCH /api/v1/profile/password`

---

## 6. Bot 侧接口（对应 `bot/handlers`）

> 当前 Bot handler 以占位回复为主；以下接口为数据库对接后必需。

1. `GET /api/v1/bot/catalog/categories?type=full|basic|special`
2. `GET /api/v1/bot/catalog/items?category_id=&country=&bin=&page=`
3. `GET /api/v1/bot/bin/{bin_number}`
4. `GET /api/v1/bot/merchants`
5. `GET /api/v1/bot/merchants/{id}/items`
6. `POST /api/v1/bot/cart/items`
7. `GET /api/v1/bot/cart`
8. `DELETE /api/v1/bot/cart/items/{id}`
9. `POST /api/v1/bot/orders/checkout`
10. `GET /api/v1/bot/orders`
11. `POST /api/v1/bot/deposits/create`
12. `GET /api/v1/bot/deposits/{id}`
13. `GET /api/v1/bot/balance`

Bot 侧核心权限：
- 用户只可访问自己的资源（user_id + bot_id 双因子）
- checkout 必须库存行级锁定（防并发超卖）
- 支付回调必须验签/验链上 tx hash 唯一

---

## 7. 关键事务与一致性要求

1. 订单退款事务
- 更新 `orders.status=refunded`
- 回补用户余额
- 写入 `balance_ledger(action=refund)`
- 写入 `admin_audit_log`

2. 手动充值事务
- 创建 `deposits(method=manual,status=completed)`
- 更新 `users.balance` 与 `users.total_deposit`
- 写入 `balance_ledger(action=manual_credit)`

3. 库存导入事务
- 创建 `inventory_import_task`
- 批量入库 `product_items`
- 更新 `inventory_library` 统计
- 开启推送时写 `push_review_task`

4. 推送任务事务
- 审核通过 -> 入队 -> 发送结果回写
- 全链路写 `push_message_audit_logs`

---

## 8. 对照结论（与前端功能一一对应）

1. 已能覆盖的大模块
- 代理、商家、Bot、订单、充值、推送主任务、用户基础、BIN、分类、商品、钱包

2. 当前最大缺口（必须补）
- 库维度模型（InventoryLibrary）
- 导入任务模型（InventoryImportTask）
- 用户多来源 Bot（UserBotSource）
- 余额流水台账（BalanceLedger）
- 导出任务模型（ExportTask）
- 推送审核表（PushReviewTask）
- 系统设置持久化（SystemSetting）

3. 不补这些会导致的问题
- 库存页无法和数据库结构一一对应
- 余额/退款不可审计
- 导出任务无法可追踪/可恢复
- 推送审核仅内存态，服务重启丢数据
- settings 页无法持久化

---

## 9. 建议迁移顺序（数据库对接实施）

1. 先落库基础审计与配置
- `SystemSetting`、`AdminAuditLog`、`BalanceLedger`

2. 再补库存与导入链路
- `InventoryLibrary`、`InventoryImportTask`

3. 再补用户多来源与导出链路
- `UserBotSource`、`ExportTask`

4. 最后切推送审核落库
- `PushReviewTask`，并将 `services/push_queue.py` 从内存仓储切 DB 仓储

---

## 10. 最终交付标准（验收）

- 所有页面动作都有对应 API（含筛选、分页、详情、写操作）
- 所有写操作都有角色校验 + 数据域校验 + 审计日志
- 所有金额变更都落 `BalanceLedger`
- 所有长任务（导入/导出/推送）都有任务表与状态机
- ORM 字段命名、状态枚举、金额/时间类型全部统一

