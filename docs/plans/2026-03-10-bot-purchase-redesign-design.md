# Bot Purchase Redesign Design

## Scope

This design implements a bot-side purchase flow redesign with aligned frontend, ORM, and database behavior.

Core constraints confirmed with the user:
- Remove bot-side `购物车` and `订单记录` buttons and interaction paths.
- Keep backend order persistence for audit and finance.
- Category mapping:
  - `全资库` -> `全资库 一手` + `全资库 二手`
  - `裸资库` -> `裸资库`
  - `特价库` -> `特价库`
- Library-level purchase entry:
  - `挑头购买`
  - `随机购买`
  - `实时卡头库存` (txt, one BIN per line)
  - `3头C卡` .. `6头C卡` and `3头D卡` .. `6头D卡`
- `3/4/5/6头` means BIN first digit equals 3/4/5/6.
- `C/D` means `bin_info.card_type` is CREDIT/DEBIT.
- Price source for all library purchase modes is `inventory_libraries.pick_price`.
- Balance check is strict: insufficient if `balance < payable_total`.

## Bot Flow

1. Main menu:
   - Row 1: 全资库 / 裸资库 / 特价库
   - Row 2: 商家基地 / 卡头查询 / 全球卡头库存
   - Row 3: 充值 / 余额查询 / English

2. Category -> libraries:
   - Click category button, show category entry buttons.
   - Click category entry, show:
     - `分类名-【总库存数量】`
     - Inline buttons: `库名称【剩余数量】`

3. Library detail:
   - Show library summary and options:
     - 挑头购买【价格】
     - 随机购买【价格】
     - 实时卡头库存
     - 3头C卡/3头D卡 .. 6头C卡/6头D卡 with `【单价】【库存剩余数量】`

4. Purchase modes:
   - Head mode:
     - Prompt for BIN input with validation and multi-format parsing (newline, `,`, `，`).
     - For missing BINs, return stock warning text.
     - If exists, prompt quantity.
     - Quantity applies per BIN (`N` per BIN).
   - Random mode:
     - Prompt quantity only.
   - Prefix mode (3-6 + C/D):
     - Prompt quantity only.

5. Card search:
   - Global available-inventory BIN search.
   - Return matched libraries as buttons:
     - `库名称【该BIN剩余数量】【挑头价格】`
   - Click any library button to open library detail actions.

6. Files:
   - `全球卡头库存` exports all sellable BINs from all libraries, unique, one per line.
   - Filename: `YYYY-MM-DD-全局卡头库存.txt`.
   - Library-level realtime BIN file also exported as txt.

7. Recharge:
   - Manual amount input.
   - Range: `30` to `10000` USDT, max 2 decimals.
   - Response includes address, amount, expiry (UTC+8), warning text, and QR code.

8. Delivery:
   - Success response sends purchased content from `product_items.raw_data` only.

## Data/ORM/DB

- ORM additions:
  - `InventoryLibrary.is_bot_enabled: bool` (default true, indexed).
  - `OrderItem.purchase_mode: Optional[str]`.
  - `OrderItem.purchase_filter_json: Optional[str]`.
- Product query indexes for library purchase:
  - `(inventory_library_id, status, bin_number)`
  - `(inventory_library_id, status, created_at)`
- Runtime DB patch ensures columns/indexes exist in current PostgreSQL.

## Quality

- Remove bot-side cart/order handlers and buttons.
- Add service-layer purchase helpers and bot flow state machine.
- Add/adjust tests for category mapping and service behavior.
