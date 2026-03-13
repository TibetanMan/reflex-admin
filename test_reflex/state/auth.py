"""Authentication state with DB-backed admin login."""

import reflex as rx

from services.auth_api import authenticate_admin
from shared.models.admin_user import AdminRole


class AuthState(rx.State):
    """Authentication and role state for admin console."""

    is_logged_in: bool = False
    username: str = ""
    user_name: str = ""
    user_role: str = ""
    user_avatar: str = ""

    login_username: str = ""
    login_password: str = ""
    remember_me: bool = False
    is_loading: bool = False
    error_message: str = ""

    def set_login_username(self, value: str):
        self.login_username = value
        self.error_message = ""

    def set_login_password(self, value: str):
        self.login_password = value
        self.error_message = ""

    def set_remember_me(self, value: bool):
        self.remember_me = value

    def handle_login(self):
        """Handle login against persisted admin users."""
        self.is_loading = True

        if not self.login_username or not self.login_password:
            self.error_message = "Please enter username and password"
            self.is_loading = False
            return

        user = authenticate_admin(self.login_username, self.login_password)
        if user:
            self.is_logged_in = True
            self.username = str(user.get("username") or self.login_username)
            self.user_name = str(user.get("display_name") or self.username)
            self.user_role = str(user.get("role") or "")
            self.user_avatar = str(user.get("avatar_url") or "")
            self.error_message = ""
            self.is_loading = False
            self.login_username = ""
            self.login_password = ""
            return rx.redirect("/")

        self.error_message = "Invalid username or password"
        self.is_loading = False

    def handle_logout(self):
        """Logout and clear auth state."""
        self.is_logged_in = False
        self.username = ""
        self.user_name = ""
        self.user_role = ""
        self.user_avatar = ""
        return rx.redirect("/login")

    def check_auth(self):
        """Guard private pages."""
        if not self.is_logged_in:
            return rx.redirect("/login")

    @rx.var
    def is_super_admin(self) -> bool:
        return self.user_role == AdminRole.SUPER_ADMIN.value

    @rx.var
    def is_agent(self) -> bool:
        return self.user_role == AdminRole.AGENT.value

    @rx.var
    def is_merchant(self) -> bool:
        return self.user_role == AdminRole.MERCHANT.value

    @rx.var
    def role_display(self) -> str:
        role_names = {
            AdminRole.SUPER_ADMIN.value: "Super Admin",
            AdminRole.AGENT.value: "Agent",
            AdminRole.MERCHANT.value: "Merchant",
        }
        return role_names.get(self.user_role, "Unknown")

    @rx.var
    def can_manage_bots(self) -> bool:
        return self.user_role in [AdminRole.SUPER_ADMIN.value, AdminRole.AGENT.value]

    @rx.var
    def can_manage_inventory(self) -> bool:
        return self.user_role in [AdminRole.SUPER_ADMIN.value, AdminRole.MERCHANT.value]

    @rx.var
    def can_manage_agents(self) -> bool:
        return self.user_role == AdminRole.SUPER_ADMIN.value

    @rx.var
    def can_view_all_data(self) -> bool:
        return self.user_role == AdminRole.SUPER_ADMIN.value
