# Admin Account Security Hardening Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enforce strict admin security boundaries (auth/authz, credential policy, profile identity safety) first, then complete account usability gaps (password change UI and controlled register/forgot-password flows).

**Architecture:** Introduce a centralized request security gate at the API dispatcher boundary, remove all unsafe `"admin"` fallback behavior, and enforce weak-password fail-fast at startup. After high-priority hardening is green, add medium-priority account UX flows using existing service contracts and controlled admin lifecycle routes.

**Tech Stack:** Python 3.12, SQLModel, Reflex state/pages, pytest, uv

---

## Skills To Apply During Execution

- `@superpowers/test-driven-development`
- `@superpowers/verification-before-completion`
- `@superpowers/systematic-debugging` (only if verification fails unexpectedly)

## Scope Check

This plan targets one coherent subsystem (admin security + account lifecycle in admin console) with two ordered priority phases:
- High priority: security boundary hardening (must finish first).
- Medium priority: account usability completion on top of hardened baseline.

## File Structure (Lock Before Coding)

- Create: `services/security_errors.py`
  - Responsibility: canonical security exception types (`AuthRequiredError`, `PermissionDeniedError`, `SecurityPolicyError`).
- Create: `services/request_security.py`
  - Responsibility: actor resolution + route policy enforcement for dispatcher.
- Modify: `services/reflex_api.py`
  - Responsibility: enforce pre-dispatch auth/authz and remove unsafe operator fallbacks.
- Modify: `services/profile_service.py`
  - Responsibility: remove implicit profile user fallback behavior.
- Modify: `shared/bootstrap.py`
  - Responsibility: fail-fast credential policy checks during startup.
- Modify: `shared/config.py`
  - Responsibility: add required startup password policy settings.
- Modify: `.env.example`
  - Responsibility: document mandatory secure bootstrap password settings.
- Modify: `services/agent_service.py`
  - Responsibility: eliminate fixed weak default password in agent admin creation.
- Modify: `services/merchant_service.py`
  - Responsibility: eliminate fixed weak default password in merchant admin creation.
- Modify: `test_reflex/state/profile_state.py`
  - Responsibility: add password-change state flow and wire to profile API.
- Modify: `test_reflex/pages/profile.py`
  - Responsibility: add password-change modal/action UX.
- Modify: `test_reflex/pages/login.py`
  - Responsibility: replace placeholder register/forgot links with controlled real flows.
- Create: `test_reflex/pages/account_access_help.py`
  - Responsibility: controlled register/forgot-password guidance page(s).
- Modify: `test_reflex/test_reflex.py`
  - Responsibility: register controlled account help page routes.
- Create: `services/admin_account_service.py`
  - Responsibility: super-admin-only controlled admin account creation/reset entrypoints.
- Modify: `services/reflex_api.py`
  - Responsibility: expose protected admin account management route(s).
- Create: `tests/services/test_request_security.py`
  - Responsibility: unit tests for route policy and actor resolution behavior.
- Modify: `tests/api/test_phase2_http_api_bridge.py`
  - Responsibility: route-level auth/authz enforcement and security propagation assertions.
- Modify: `tests/services/test_profile_service.py`
  - Responsibility: identity safety tests (no super-admin implicit fallback).
- Modify: `tests/test_bootstrap_super_admin.py`
  - Responsibility: startup weak-password fail-fast tests.
- Modify: `tests/test_settings_profile_inventory_db_bridge.py`
  - Responsibility: ensure profile state uses password update service call.
- Create: `tests/test_profile_password_flow.py`
  - Responsibility: profile password UI/state bridge assertions.
- Create: `tests/test_login_account_help_links.py`
  - Responsibility: ensure login links are real flows, not `href="#"`.
- Create: `tests/services/test_admin_account_service.py`
  - Responsibility: controlled admin account create/reset permission and policy tests.

## Preflight

### Task 0: Baseline and Workspace Safety

**Files:**
- Modify: none
- Test: none

- [ ] **Step 1: Confirm workspace and branch state**

Run: `git status --short`
Expected: inspect current tree before edits.

- [ ] **Step 2: Run targeted baseline suites (no `-q`)**

Run: `uv run pytest tests/services/test_auth_service.py tests/services/test_profile_service.py tests/api/test_phase2_http_api_bridge.py tests/test_bootstrap_super_admin.py -v`
Expected: PASS baseline before hardening changes.

---

## Chunk 1: High Priority H1 - Dispatch Security Gate and Unsafe Fallback Removal

### Task 1: Add failing tests for request security policy and actor requirements

**Files:**
- Create: `tests/services/test_request_security.py`
- Modify: `tests/api/test_phase2_http_api_bridge.py`
- Test: same files

- [ ] **Step 1: Add failing unit tests for actor required / role required policy**

```python
def test_enforce_route_policy_requires_actor_for_protected_write():
    with pytest.raises(AuthRequiredError):
        enforce_route_policy(method="POST", path="/api/v1/finance/deposits/manual", body={})


def test_enforce_route_policy_rejects_non_super_admin_for_super_admin_route():
    with pytest.raises(PermissionDeniedError):
        enforce_route_policy(
            method="PUT",
            path="/api/v1/settings/default-usdt-address",
            body={"actor_username": "agent1"},
            actor_role="agent",
        )
```

- [ ] **Step 2: Add failing dispatcher bridge tests for auth/authz failures**

```python
def test_dispatch_rejects_missing_actor_on_sensitive_write(monkeypatch):
    ...
    with pytest.raises(AuthRequiredError):
        module.dispatch_request("POST", "/api/v1/finance/deposits/manual", {"amount": "10"})
```

- [ ] **Step 3: Run targeted tests to verify RED**

Run: `uv run pytest tests/services/test_request_security.py tests/api/test_phase2_http_api_bridge.py -k "actor or permission or auth" -v`
Expected: FAIL due missing security module/guard behavior.

### Task 2: Implement security error types and route policy engine

**Files:**
- Create: `services/security_errors.py`
- Create: `services/request_security.py`
- Test: `tests/services/test_request_security.py`

- [ ] **Step 1: Implement canonical security exceptions**

```python
class AuthRequiredError(PermissionError): ...
class PermissionDeniedError(PermissionError): ...
class SecurityPolicyError(RuntimeError): ...
```

- [ ] **Step 2: Implement route policy table and actor/role enforcement helpers**

```python
def enforce_route_policy(*, method: str, path: str, body: dict[str, Any], actor_role: str | None) -> None:
    ...
```

- [ ] **Step 3: Run unit tests to verify GREEN**

Run: `uv run pytest tests/services/test_request_security.py -v`
Expected: PASS.

### Task 3: Integrate security gate into dispatcher and remove unsafe `"admin"` fallback

**Files:**
- Modify: `services/reflex_api.py`
- Modify: `tests/api/test_phase2_http_api_bridge.py`
- Test: same files

- [ ] **Step 1: Add pre-dispatch security enforcement call in `dispatch_request`**

```python
actor = resolve_actor_from_payload(body)
enforce_route_policy(method=m, path=p, body=body, actor_role=actor.role if actor else None)
```

- [ ] **Step 2: Replace `operator_username or "admin"` patterns with explicit actor-provided value**

Delete fallback behavior that implicitly defaults operator identity to `"admin"` in protected writes.

- [ ] **Step 3: Update bridge tests to pass explicit actor context where required**

Ensure tests intentionally verify both deny-path and allow-path behavior.

- [ ] **Step 4: Run targeted dispatcher tests**

Run: `uv run pytest tests/api/test_phase2_http_api_bridge.py -k "auth or permission or finance or settings" -v`
Expected: PASS with explicit actor behavior.

### Task 4: Remove profile implicit fallback-to-super-admin behavior

**Files:**
- Modify: `services/profile_service.py`
- Modify: `tests/services/test_profile_service.py`
- Test: same file

- [ ] **Step 1: Add failing tests for missing identity rejection**

```python
def test_get_profile_snapshot_raises_when_username_missing(...):
    with pytest.raises(ValueError, match="username"):
        get_profile_snapshot(username="", ...)
```

- [ ] **Step 2: Run targeted tests to verify RED**

Run: `uv run pytest tests/services/test_profile_service.py -k "missing or fallback or password" -v`
Expected: FAIL because current behavior falls back to super admin.

- [ ] **Step 3: Implement strict identity selection**

Require explicit non-empty username for profile read/update/password change paths.

- [ ] **Step 4: Re-run targeted tests to verify GREEN**

Run: `uv run pytest tests/services/test_profile_service.py -v`
Expected: PASS.

- [ ] **Step 5: Commit chunk**

```bash
git add services/security_errors.py services/request_security.py services/reflex_api.py services/profile_service.py tests/services/test_request_security.py tests/api/test_phase2_http_api_bridge.py tests/services/test_profile_service.py
git commit -m "feat: enforce dispatch authz boundary and strict profile identity"
```

---

## Chunk 2: High Priority H2 - Startup Credential Policy Fail-Fast

### Task 5: Add failing tests for weak/default password startup blocking

**Files:**
- Modify: `tests/test_bootstrap_super_admin.py`
- Test: same file

- [ ] **Step 1: Add failing test for startup blocking weak super-admin password**

```python
def test_run_startup_bootstrap_raises_on_weak_super_admin_password(monkeypatch):
    ...
    with pytest.raises(SecurityPolicyError):
        bootstrap_module.run_startup_bootstrap()
```

- [ ] **Step 2: Add failing test for strong password pass-through**

```python
def test_run_startup_bootstrap_accepts_strong_password(monkeypatch):
    ...
```

- [ ] **Step 3: Run tests to verify RED**

Run: `uv run pytest tests/test_bootstrap_super_admin.py -k "weak or strong or policy" -v`
Expected: FAIL before policy implementation.

### Task 6: Implement startup password policy and remove fixed weak defaults

**Files:**
- Modify: `shared/config.py`
- Modify: `shared/bootstrap.py`
- Modify: `services/agent_service.py`
- Modify: `services/merchant_service.py`
- Modify: `.env.example`
- Test: `tests/test_bootstrap_super_admin.py`

- [ ] **Step 1: Add security settings fields for bootstrap password policy**

Add explicit settings for secure super-admin bootstrap password and policy toggles (strict by default).

- [ ] **Step 2: Implement weak/default password validator**

```python
def validate_bootstrap_password_policy(...):
    ...
    if is_weak_or_default(password):
        raise SecurityPolicyError(...)
```

- [ ] **Step 3: Call validator from startup bootstrap path before account bootstrap**

Ensure app fails fast when policy is violated.

- [ ] **Step 4: Replace hardcoded `agent123` / `merchant123` creation defaults**

Use secure generation or explicit required input according to strict policy.

- [ ] **Step 5: Update `.env.example` docs with required secure values**

Document mandatory strong bootstrap password for runtime.

- [ ] **Step 6: Run targeted tests to verify GREEN**

Run: `uv run pytest tests/test_bootstrap_super_admin.py tests/services/test_auth_service.py -v`
Expected: PASS.

- [ ] **Step 7: Commit chunk**

```bash
git add shared/config.py shared/bootstrap.py services/agent_service.py services/merchant_service.py .env.example tests/test_bootstrap_super_admin.py
git commit -m "feat: enforce startup credential policy and remove weak defaults"
```

---

## Chunk 3: Medium Priority M1 - Profile Password-Change UX

### Task 7: Add failing state/page tests for password-change flow

**Files:**
- Modify: `tests/test_settings_profile_inventory_db_bridge.py`
- Create: `tests/test_profile_password_flow.py`
- Test: same files

- [ ] **Step 1: Add failing bridge assertion that profile state calls password update service**

```python
assert "update_profile_password(" in password_source
```

- [ ] **Step 2: Add failing state tests for validation and success behavior**

```python
def test_profile_state_change_password_requires_confirmation_match(...): ...
def test_profile_state_change_password_calls_service_and_resets_fields(...): ...
```

- [ ] **Step 3: Run tests to verify RED**

Run: `uv run pytest tests/test_settings_profile_inventory_db_bridge.py tests/test_profile_password_flow.py -v`
Expected: FAIL before state/page implementation.

### Task 8: Implement profile password-change state and UI

**Files:**
- Modify: `test_reflex/state/profile_state.py`
- Modify: `test_reflex/pages/profile.py`
- Test: `tests/test_profile_password_flow.py`

- [ ] **Step 1: Add password-change fields and handlers in `ProfileState`**

Include current/new/confirm fields, validation, and service call to `update_profile_password`.

- [ ] **Step 2: Add modal and action button in profile page**

Use existing page style patterns; avoid introducing unrelated layout changes.

- [ ] **Step 3: Ensure success path enforces re-login or explicit security prompt**

Return deterministic event behavior for tests.

- [ ] **Step 4: Run focused tests to verify GREEN**

Run: `uv run pytest tests/test_profile_password_flow.py tests/test_settings_profile_inventory_db_bridge.py -k "profile" -v`
Expected: PASS.

- [ ] **Step 5: Commit chunk**

```bash
git add test_reflex/state/profile_state.py test_reflex/pages/profile.py tests/test_profile_password_flow.py tests/test_settings_profile_inventory_db_bridge.py
git commit -m "feat: add profile password change workflow"
```

---

## Chunk 4: Medium Priority M2 - Controlled Register/Forgot-Password and Admin Account Lifecycle

### Task 9: Add failing tests for login links and controlled access pages

**Files:**
- Create: `tests/test_login_account_help_links.py`
- Test: same file

- [ ] **Step 1: Add failing test asserting login page has no `href=\"#\"` auth placeholders**

```python
def test_login_page_has_real_register_and_forgot_password_routes():
    ...
```

- [ ] **Step 2: Add failing test asserting controlled help routes exist in app entry**

```python
def test_app_registers_account_access_help_pages():
    ...
```

- [ ] **Step 3: Run tests to verify RED**

Run: `uv run pytest tests/test_login_account_help_links.py -v`
Expected: FAIL until page/routes are implemented.

### Task 10: Implement controlled register/forgot-password real flows

**Files:**
- Modify: `test_reflex/pages/login.py`
- Create: `test_reflex/pages/account_access_help.py`
- Modify: `test_reflex/test_reflex.py`
- Test: `tests/test_login_account_help_links.py`

- [ ] **Step 1: Replace placeholder links in login page with real routes**

`/account/request-access` and `/account/password-reset-help` (or equivalent controlled paths).

- [ ] **Step 2: Implement controlled help pages with clear policy copy**

No anonymous self-registration/reset execution in this phase.

- [ ] **Step 3: Register routes in app entry**

Ensure pages are reachable and tested.

- [ ] **Step 4: Run focused tests to verify GREEN**

Run: `uv run pytest tests/test_login_account_help_links.py tests/test_auth_state_db_login.py -v`
Expected: PASS.

### Task 11: Add controlled admin account management service (super-admin only)

**Files:**
- Create: `services/admin_account_service.py`
- Modify: `services/reflex_api.py`
- Create: `tests/services/test_admin_account_service.py`
- Modify: `tests/api/test_phase2_http_api_bridge.py`
- Test: same files

- [ ] **Step 1: Add failing service tests for create/reset guarded by super-admin role**

```python
def test_create_admin_account_rejects_non_super_admin(...): ...
def test_create_admin_account_generates_secure_initial_password(...): ...
```

- [ ] **Step 2: Run tests to verify RED**

Run: `uv run pytest tests/services/test_admin_account_service.py -v`
Expected: FAIL (service not implemented).

- [ ] **Step 3: Implement minimal super-admin-only admin account create/reset logic**

Include audit-friendly return payload for initial credential handoff.

- [ ] **Step 4: Expose protected route(s) in dispatcher and add route tests**

Example path: `POST /api/v1/admin/accounts`.

- [ ] **Step 5: Run focused tests to verify GREEN**

Run: `uv run pytest tests/services/test_admin_account_service.py tests/api/test_phase2_http_api_bridge.py -k "admin account" -v`
Expected: PASS.

- [ ] **Step 6: Commit chunk**

```bash
git add services/admin_account_service.py services/reflex_api.py test_reflex/pages/login.py test_reflex/pages/account_access_help.py test_reflex/test_reflex.py tests/test_login_account_help_links.py tests/services/test_admin_account_service.py tests/api/test_phase2_http_api_bridge.py
git commit -m "feat: add controlled account access flows and admin account lifecycle APIs"
```

---

## Chunk 5: Final Verification and Completion

### Task 12: Full verification before completion

**Files:**
- Modify: none
- Test: existing suites

- [ ] **Step 1: Compile critical modules**

Run: `uv run python -m py_compile services/security_errors.py services/request_security.py services/reflex_api.py shared/bootstrap.py services/profile_service.py test_reflex/state/profile_state.py test_reflex/pages/profile.py test_reflex/pages/login.py test_reflex/pages/account_access_help.py services/admin_account_service.py`
Expected: no output, exit code 0.

- [ ] **Step 2: Run security/account core regression set**

Run: `uv run pytest tests/services/test_request_security.py tests/services/test_auth_service.py tests/services/test_profile_service.py tests/test_bootstrap_super_admin.py tests/api/test_phase2_http_api_bridge.py tests/test_auth_state_db_login.py tests/test_settings_profile_inventory_db_bridge.py tests/test_profile_password_flow.py tests/test_login_account_help_links.py tests/services/test_admin_account_service.py -v`
Expected: all PASS.

- [ ] **Step 3: Run impacted functional suites (non-`-q`)**

Run: `uv run pytest tests/test_finance_state_db_bridge.py tests/test_operator_username_binding.py tests/test_settings_profile_inventory_db_bridge.py tests/test_push_page.py tests/test_inventory_page.py -v`
Expected: PASS with no new security regressions.

- [ ] **Step 4: Final commit**

```bash
git add services/security_errors.py services/request_security.py services/reflex_api.py shared/bootstrap.py shared/config.py .env.example services/profile_service.py services/agent_service.py services/merchant_service.py test_reflex/state/profile_state.py test_reflex/pages/profile.py test_reflex/pages/login.py test_reflex/pages/account_access_help.py test_reflex/test_reflex.py services/admin_account_service.py tests/services/test_request_security.py tests/services/test_profile_service.py tests/test_bootstrap_super_admin.py tests/api/test_phase2_http_api_bridge.py tests/test_settings_profile_inventory_db_bridge.py tests/test_profile_password_flow.py tests/test_login_account_help_links.py tests/services/test_admin_account_service.py
git commit -m "feat: harden admin security boundary and complete account lifecycle flows"
```

## Done Definition

- Protected write routes cannot execute without explicit authenticated actor identity.
- Role-restricted routes consistently enforce backend role checks.
- Unsafe `"admin"` operator fallback is removed from protected write paths.
- Startup fails fast on weak/default bootstrap credentials.
- Profile read/update/password paths no longer fallback to super-admin implicitly.
- Profile password-change flow is available and tested.
- Login register/forgot-password entries are real controlled flows, not placeholders.
- Controlled super-admin account lifecycle path exists and is tested.
