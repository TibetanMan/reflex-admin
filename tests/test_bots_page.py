import test_reflex.pages.bots as bots_page_module
from test_reflex.pages.bots import render_bot_row


class _Revenue:
    def __init__(self, value: float):
        self.value = value

    def to(self, _type):
        return str(self.value)


class _Bot:
    def __init__(self):
        self.id = 9
        self.name = "Sample Bot"
        self.username = "@sample_bot"
        self.token_masked = "1234...abcd"
        self.status = "active"
        self.owner = "平台自营"
        self.users = 1
        self.orders = 1
        self.revenue = _Revenue(1.0)


def _has_tooltip_fragment_child(node) -> bool:
    if isinstance(node, dict):
        if node.get("name") == "RadixThemesTooltip":
            children = node.get("children", [])
            if children and isinstance(children[0], dict) and children[0].get("name") == "Fragment":
                return True
        for child in node.get("children", []):
            if _has_tooltip_fragment_child(child):
                return True
        return False

    if isinstance(node, list):
        return any(_has_tooltip_fragment_child(child) for child in node)

    return False


def test_bot_rows_tooltip_children_are_not_fragments():
    sample = _Bot()

    render_trees = [
        render_bot_row(sample).render(),
    ]

    assert all(not _has_tooltip_fragment_child(tree) for tree in render_trees)


def test_legacy_demo_rows_are_removed_from_bots_page_module():
    assert not hasattr(bots_page_module, "bot_row_1")
    assert not hasattr(bots_page_module, "bot_row_2")
    assert not hasattr(bots_page_module, "bot_row_3")


def test_bots_page_does_not_bool_cast_runtime_selected_var():
    import inspect

    source = inspect.getsource(bots_page_module.render_bot_row)
    assert 'bool(getattr(bot, "runtime_selected"' not in source
