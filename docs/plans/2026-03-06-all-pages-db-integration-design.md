# 2026-03-06 全页面数据库对接设计（阶段一先完成）

## 1. 背景与目标

本次目标是将 `test_reflex` 所有页面中的数据展示与交互，完全对接 PostgreSQL（Docker），并在空库启动时自动创建默认超级管理员账号：

- 用户名：`admin`
- 密码：`admin123`

已确认约束：

1. 交付策略采用两阶段：
- 阶段一：`Reflex State -> services/repository -> SQLModel(PostgreSQL)`
- 阶段二：`Reflex State -> HTTP API -> services -> DB`

2. 阶段一必须 DB-only：
- 运行时不允许回退内存仓库
- 测试也不使用内存仓库替代业务主链路

3. 启动初始化策略：
- 空库自动初始化默认超级管理员
- 空库自动注入演示种子数据（覆盖各页面）

4. 交付节奏：
- 阶段一一次性完整交付并通过回归测试，再开始阶段二 API 化

---

## 2. 总体架构（阶段一）

### 2.1 架构原则

统一采用以下调用链：

- 页面组件：负责 UI 结构与事件绑定
- State：负责 UI 状态管理、参数拼装、调用 service、错误提示
- Service/Repository：负责业务规则、事务边界、数据库读写
- SQLModel/PostgreSQL：唯一数据源

State 中移除硬编码演示列表，改为 `load_*` 查询数据库。所有按钮事件（新增/编辑/删除/状态变更/导入导出/审核）必须落库。

### 2.2 模块分层

新增或重构服务层模块：

- `services/auth_service.py`
- `services/dashboard_service.py`
- `services/bot_service.py`
- `services/agent_service.py`
- `services/merchant_service.py`
- `services/inventory_service.py`
- `services/order_service.py`
- `services/user_service.py`
- `services/finance_service.py`
- `services/settings_service.py`

保留并改造既有仓储模块为 DB-only：

- `services/push_queue.py`
- `services/export_task.py`

### 2.3 并行开发拆分

为提高效率，阶段一内部并行拆成四条开发流：

1. 认证与权限流：`auth + RBAC + 默认超管`
2. 核心交易流：`orders + users + finance`
3. 运营流：`inventory + push + export`
4. 管理流：`bots + agents + merchants + settings + dashboard`

最终在主线统一联调并执行全量回归。

---

## 3. 数据模型与约束治理

### 3.1 模型使用范围

现有 `shared/models/*` 已覆盖大多数业务域：

- 账号权限：`AdminUser`, `Agent`, `Merchant`
- 业务实体：`BotInstance`, `User`, `Order`, `OrderItem`, `ProductItem`, `Deposit`, `WalletAddress`
- 运营能力：`InventoryLibrary`, `InventoryImportTask`, `InventoryImportLineError`, `PushReviewTask`, `PushMessageTask`, `PushMessageAuditLog`, `ExportTask`
- 审计与设置：`AdminAuditLog`, `BalanceLedger`, `SystemSetting`

阶段一优先复用现有模型，不引入不必要新表。

### 3.2 关键治理项

1. 金额字段治理（优先关键链路）：
- 优先保证 `BalanceLedger`、订单/充值/余额调整相关字段在数据库中的精度稳定
- 业务逻辑层统一使用 `Decimal` 处理金额

2. 关系与索引治理：
- 核心过滤字段建立索引：状态、时间、归属主体（bot/agent/merchant/user）
- 核心关联字段保持完整性检查

3. 审计落库：
- 退款、余额调整、推送审批、设置修改等动作写 `AdminAuditLog`

---

## 4. 启动初始化与默认超管

### 4.1 初始化入口

新增 `shared/bootstrap.py`（或同等入口），应用启动时执行：

1. `init_db()`：创建表结构
2. `bootstrap_super_admin()`：确保 `admin` 存在
3. `bootstrap_seed_if_empty()`：核心表为空时写入演示数据

### 4.2 默认超级管理员策略

- 用户名固定：`admin`
- 初始密码：`admin123`
- 数据库存储：密码哈希（禁止明文）
- 角色：`super_admin`

### 4.3 种子数据范围

种子覆盖所有页面最小可用数据：

- bots/agents/merchants
- users/orders/order_items/deposits/wallets
- inventory/import_tasks
- push_review/push_message
- settings/dashboard 统计基础数据

幂等要求：重复启动不会写入重复种子（基于唯一键与存在性检查）。

---

## 5. 页面改造映射

### 5.1 认证与权限

- `AuthState` 移除 `TEST_USERS`
- 登录改为数据库校验，写 `last_login_at`
- 角色权限变量由数据库角色派生

### 5.2 页面级对接清单

1. `dashboard`
- 全部统计与列表来自聚合查询

2. `bots / agents / merchants`
- 列表分页、筛选、创建编辑、状态切换全部落库

3. `inventory`
- 库列表、导入任务、价格调整、启停/删除落库
- 导入触发时写 `InventoryImportTask`

4. `orders`
- 列表与详情查询数据库
- 退款采用事务：订单状态 + 余额回滚 + 审计
- 导出任务继续走 `ExportTask` DB 仓储

5. `users`
- 列表/详情/封禁落库
- 余额调整写 `BalanceLedger`，保证幂等（request_id）

6. `finance`
- 充值记录、手动充值、钱包列表全部落库

7. `push`
- 审核与推送队列继续使用 DB repository

8. `settings`
- 配置读取与更新统一落 `SystemSetting`

9. `profile`
- 读取当前登录管理员的数据库信息

---

## 6. 错误处理与事务边界

1. 所有写操作放在 service 层事务边界内：
- 成功提交
- 失败回滚并返回可展示错误

2. 高风险操作必须幂等：
- 余额调整：`request_id` 唯一约束
- 推送任务：`dedup_key` 去重

3. DB-only 失败策略：
- 连接失败/初始化失败时应用显式失败
- 不允许静默回退内存实现

---

## 7. 测试策略与验收标准

### 7.1 测试策略

阶段一采用 DB 集成优先：

1. Service 集成测试
- 真实 PostgreSQL 上验证 CRUD、分页筛选、事务、幂等、权限域

2. State-Bridge 测试
- 验证 State 是否调用正确 service，并在成功后刷新列表状态

3. 页面绑定回归
- 保留 `repr` 级绑定测试，确保关键 handler 不丢失

### 7.2 验收标准

必须全部满足：

1. 所有页面数据来自 PostgreSQL
2. 默认超管 `admin/admin123` 可登录
3. 关键业务动作可审计可追踪
4. 全量测试通过
5. 启动失败显式报错，无内存回退

---

## 8. 阶段二预留（API 化）

阶段二将把阶段一稳定的 service 能力上提为 HTTP API：

- 统一前缀 `/api/v1`
- JWT 会话与鉴权
- State 从“直连 service”切换到“调用 API client”
- 保持阶段一业务语义与测试用例可迁移

阶段二不改变核心数据库模型与事务语义，仅替换调用路径。

---

## 9. 实施顺序（阶段一）

1. 启动初始化与默认超管（auth + bootstrap）
2. 核心交易链路（orders/users/finance）
3. 运营链路（inventory/push/export）
4. 管理与聚合页（bots/agents/merchants/settings/dashboard/profile）
5. 全量回归与联调验收

该顺序确保先打通登录和高频交易路径，再收敛外围管理页面，降低集成风险。
