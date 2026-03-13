import reflex as rx

from test_reflex.pages.users import user_actions, user_activity_drawer
from test_reflex.state.user_state import UserState
from test_reflex.components.a11y import with_focus_blur


def test_with_focus_blur_prefixes_blur_script_before_overlay_event():
    events = with_focus_blur(UserState.open_export_modal)

    assert isinstance(events, list)
    assert len(events) == 2
    assert isinstance(events[0], rx.event.EventSpec)
    assert events[0].args[0][1]._var_value == "document.activeElement?.blur();"
    assert events[1].fn.__name__ == "open_export_modal"


def test_user_actions_blur_focus_before_opening_overlay_components():
    component = user_actions({"id": 1, "status": "active"})
    rendered = repr(component)

    assert "document.activeElement?.blur();" in rendered
    assert "open_detail_modal" in rendered
    assert "open_balance_modal" in rendered
    assert "open_user_activity_drawer" in rendered


def test_user_activity_drawer_uses_standard_right_side_fixed_width_layout():
    component = user_activity_drawer()
    rendered = repr(component)

    assert 'direction:\\"right\\"' in rendered
    assert '[\\"width\\"] : \\"520px\\"' in rendered
    assert '[\\"position\\"] : \\"fixed\\"' not in rendered
    assert '[\\"right\\"] : \\"0\\"' not in rendered
    assert '[\\"top\\"] : \\"0\\"' not in rendered
