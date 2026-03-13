from __future__ import annotations

from pathlib import Path


PAGE_DIR = Path("test_reflex/pages")
ALLOWED_WRAPPERS = (
    "rx.link(",
    "rx.dialog.close(",
    "rx.alert_dialog.cancel(",
    "rx.alert_dialog.action(",
    "rx.drawer.close(",
)


def _iter_call_blocks(source: str, call_name: str):
    start_token = f"{call_name}("
    i = 0
    while True:
        idx = source.find(start_token, i)
        if idx < 0:
            return
        depth = 0
        j = idx
        in_str: str | None = None
        escaped = False
        while j < len(source):
            ch = source[j]
            if in_str is not None:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == in_str:
                    in_str = None
            else:
                if ch in ('"', "'"):
                    in_str = ch
                elif ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
                    if depth == 0:
                        j += 1
                        break
            j += 1
        yield idx, source[idx:j]
        i = idx + 1


def _is_wrapped_by_allowed_context(source: str, idx: int) -> bool:
    context = source[max(0, idx - 220) : idx]
    return any(wrapper in context for wrapper in ALLOWED_WRAPPERS)


def test_all_page_buttons_have_action_binding_or_wrapper():
    missing: list[str] = []

    for path in sorted(PAGE_DIR.glob("*.py")):
        source = path.read_text(encoding="utf-8")
        for idx, block in _iter_call_blocks(source, "rx.button"):
            if "on_click=" in block:
                continue
            if _is_wrapped_by_allowed_context(source, idx):
                continue
            line = source.count("\n", 0, idx) + 1
            missing.append(f"{path}:{line}")

    assert not missing, "Buttons missing on_click and allowed wrapper:\n" + "\n".join(missing)


def test_all_page_icon_buttons_have_action_binding_or_wrapper():
    missing: list[str] = []

    for path in sorted(PAGE_DIR.glob("*.py")):
        source = path.read_text(encoding="utf-8")
        for idx, block in _iter_call_blocks(source, "rx.icon_button"):
            if "on_click=" in block:
                continue
            if _is_wrapped_by_allowed_context(source, idx):
                continue
            line = source.count("\n", 0, idx) + 1
            missing.append(f"{path}:{line}")

    assert not missing, "Icon buttons missing on_click and allowed wrapper:\n" + "\n".join(missing)
