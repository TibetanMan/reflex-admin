"""Accessibility helpers for focus-safe overlay interactions."""

from __future__ import annotations

from typing import Any

import reflex as rx


BLUR_ACTIVE_ELEMENT_SCRIPT = "document.activeElement?.blur();"


def blur_active_element() -> rx.event.EventSpec:
    """Blur the currently focused element in the browser."""
    return rx.call_script(BLUR_ACTIVE_ELEMENT_SCRIPT)


def with_focus_blur(event: Any) -> list[Any]:
    """Run a focus blur before dispatching an overlay-opening event."""
    return [blur_active_element(), event]
