"""Security-focused exception types for request enforcement."""

from __future__ import annotations


class AuthRequiredError(PermissionError):
    """Raised when an authenticated actor is required but missing/invalid."""


class PermissionDeniedError(PermissionError):
    """Raised when actor role lacks permission for a protected action."""


class SecurityPolicyError(RuntimeError):
    """Raised when startup/runtime security policy validation fails."""
