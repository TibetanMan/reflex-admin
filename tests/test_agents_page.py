from test_reflex.pages.agents import (
    agent_create_modal,
    agent_edit_modal,
    agent_list_table,
    agents_page,
)


def test_agents_table_renders_from_state_not_static_rows():
    component = agent_list_table()
    rendered = repr(component)

    assert "filtered_agents" in rendered
    assert "toggle_agent_status" in rendered


def test_agents_page_has_super_admin_gate():
    component = agents_page()
    rendered = repr(component)

    assert "is_super_admin" in rendered
    assert "shield-alert" in rendered


def test_agents_modals_wire_open_change_and_submit_handlers():
    create_rendered = repr(agent_create_modal())
    edit_rendered = repr(agent_edit_modal())

    assert "handle_create_modal_change" in create_rendered
    assert "save_new_agent" in create_rendered
    assert "handle_edit_modal_change" in edit_rendered
    assert "save_edit_agent" in edit_rendered
