"""Controlled account access guidance pages."""

from __future__ import annotations

import reflex as rx


def request_access_page() -> rx.Component:
    """Explain how admins request a new account from super admin."""
    return rx.container(
        rx.vstack(
            rx.heading("Request Access", size="6"),
            rx.text(
                "This admin console does not support self-registration. "
                "Please contact your super admin to request a managed account."
            ),
            rx.text("Provide your expected role, display name, and contact email to speed up approval."),
            rx.link("Back to login", href="/login"),
            spacing="4",
            align="start",
            width="100%",
        ),
        max_width="720px",
        padding="32px 24px",
    )


def password_reset_help_page() -> rx.Component:
    """Explain controlled password reset policy."""
    return rx.container(
        rx.vstack(
            rx.heading("Password Reset Help", size="6"),
            rx.text(
                "Password reset is handled by administrators only. "
                "Contact your super admin for identity verification and a secure reset."
            ),
            rx.text("Do not share OTPs or passwords through public chat channels."),
            rx.link("Back to login", href="/login"),
            spacing="4",
            align="start",
            width="100%",
        ),
        max_width="720px",
        padding="32px 24px",
    )
