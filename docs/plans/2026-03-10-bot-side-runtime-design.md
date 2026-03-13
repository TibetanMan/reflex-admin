# Bot Side Runtime Design (Phase 1)

## Goal

基于 `docs/base.md`，将 Telegram bot 从“静态菜单演示”升级为“可实时联调的交易闭环”，覆盖目录浏览、BIN 查询、购物车、结账、充值、订单和库存快照下载。

## Architecture

采用“薄 handler + 既有服务层”方案：  
`aiogram handlers` 只负责交互编排和状态机，核心业务统一走 `services/bot_side_service`（通过 `services/bot_side_api`）以复用现有数据库逻辑。  

为保证 Telegram 用户与数据库用户一致，引入运行时身份绑定模块 `bot/runtime_context.py`：  
- 以 `bot_token` 绑定/创建 `BotInstance`。  
- 以 `telegram_id` 绑定/创建 `User`，并维护活跃时间和用户资料更新。  

库存文件下载采用 `bot/renderers.py` 输出文本快照，再由 bot 直接发送 `.txt` 文件，确保“按钮即导出”。

## Implemented Scope

1. `/start` 与 `/help` 接入真实用户身份与余额读取。  
2. 主菜单接入真实业务：全资/裸资/特价分类浏览、分页查看。  
3. BIN 查询支持状态机输入与匹配商品加购。  
4. 购物车支持查看、删除、结账闭环。  
5. 充值支持快捷金额、自定义金额、状态刷新。  
6. 订单记录支持分页查看。  
7. 商家基地支持商家列表与商家库存分页浏览。  
8. 库存文件支持实时快照下载。  

## Verification

- 新增测试：  
  - `tests/bot/test_runtime_context.py`  
  - `tests/bot/test_stock_snapshot.py`  
- 回归测试：`tests/services/test_bot_side_service.py`  
- 语法检查：`python -m py_compile` 针对改动文件全部通过。  

## Live Debug Prerequisite

进入 Telegram 实时联调仅缺 `BOT_TOKEN`。  
配置后执行：`uv run python -m bot.main` 即可进入轮询。
