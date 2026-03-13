# 2026-03-13 Admin Account Security Hardening Design

## 1. Context

This spec defines a strict security-hardening and account-management plan for the admin console.

Confirmed decisions from product owner:
- Rollout strategy: immediate enforcement (no compatibility stage).
- Weak/default passwords policy: startup must fail fast when weak defaults are detected.
- Execution priority: complete high-priority security issues first, then medium-priority usability gaps.

Current project risks discovered in codebase:
- Route dispatch currently lacks a centralized authz guard in front of write operations.
- Multiple write routes still fallback `operator_username` to `"admin"`.
- Startup bootstrap and account creation flows still use default weak passwords.
- Profile service has implicit fallback user-selection behavior that can target super admin unexpectedly.
- Password-change backend exists, but there is no frontend user flow for it.
- Login page shows register/forgot-password links as placeholders (`href="#"`), which is misleading.

## 2. Problem Statement

The current admin surface has three critical classes of issues:

1. **Authorization boundary weakness**
   - Write operations can be reached without consistent identity/role checks.
   - Some write routes infer operator identity from unsafe defaults.

2. **Credential security weakness**
   - Known weak default credentials exist in bootstrap and related creation flows.
   - Environment can boot with insecure account credentials.

3. **Profile identity safety weakness**
   - Profile selection can fallback to a super-admin row when username context is missing.
   - This can cause accidental updates/password changes on the wrong account.

These must be fixed before adding new account-facing features.

## 3. Goals

- Enforce explicit identity and role checks before sensitive operations.
- Remove all unsafe operator fallbacks for write actions.
- Enforce fail-fast startup policy on weak/default passwords.
- Eliminate implicit profile-user fallback behavior.
- Keep route contracts stable where possible while tightening security semantics.
- After high-priority completion, add medium-priority usability features:
  - profile password-change UI flow,
  - non-placeholder register/forgot-password behavior with controlled account lifecycle.

## 4. Non-Goals

- No anonymous public self-registration in this phase.
- No full OAuth/SSO migration in this phase.
- No email/SMS password-reset infrastructure in this phase.
- No broad redesign of unrelated business domains (inventory/orders/push logic internals).

## 5. Priority and Scope

### 5.1 High priority (must complete first)

1. Centralized route-level auth/authz guard in request dispatch.
2. Remove `"admin"` default operator fallback from sensitive write routes.
3. Startup fail-fast for weak/default passwords.
4. Remove profile implicit fallback-to-super-admin behavior.

### 5.2 Medium priority (after high is done)

1. Add frontend password-change flow in Profile page.
2. Replace login-page register/forgot-password placeholders with controlled real flows.
3. Define controlled admin-account creation path (super-admin managed only).

## 6. Architecture Design

### 6.1 Security Gate at API Dispatch Boundary

Primary target: `services/reflex_api.py`.

Introduce a pre-dispatch security layer:
- Resolve actor identity from explicit request context (e.g., `actor_username`).
- Validate actor existence and active state from DB.
- Apply route policy checks (`require_auth`, `require_role`) before calling domain services.
- Reject unauthorized requests with explicit security errors.

Design principles:
- **Auth before business execution** for all protected routes.
- **No trust in client role claims**; role is sourced from DB by actor identity.
- **No implicit operator defaulting** in protected write paths.

### 6.2 Route Policy Model

Define route policies centrally (method + path pattern -> requirements):
- Public: only required auth endpoints like `POST /api/v1/auth/login`.
- Auth-required: session/profile/data-read endpoints requiring a valid actor.
- Role-restricted: critical writes requiring `super_admin` or appropriate role.

This policy table becomes the single source of truth for backend authorization behavior.

### 6.3 Credential Policy Hardening

Primary target: `shared/bootstrap.py` and account-creation service paths.

Strict policy:
- Startup must fail if configured bootstrap credentials are weak/default.
- Super-admin bootstrap password must be supplied securely (env-driven) and pass minimum complexity checks.
- Agent/merchant default fixed passwords are removed from runtime creation paths; replaced by generated/explicit secure credentials according to operational policy.

No degraded mode:
- If policy preconditions are not met, app startup exits with clear actionable error.

### 6.4 Profile Identity Safety

Primary target: `services/profile_service.py`.

Remove implicit user-selection fallback behavior:
- Profile read/update/password-change must use explicit authenticated identity.
- Missing/invalid identity returns explicit error.
- Never fallback to first super-admin row.

### 6.5 Error Model

Unify security and business error categories:
- `AuthRequiredError`: missing/invalid actor.
- `PermissionDeniedError`: actor exists but role lacks permission.
- `SecurityPolicyError`: startup or credential policy violation.
- Existing `ValueError`: business validation (amount, required fields, etc.).

State/UI layers should surface these categories with clear user-facing messages, without silently downgrading to default identities.

## 7. Data Flow

### 7.1 Protected request flow

1. Incoming request reaches `dispatch_request`.
2. Route policy is resolved.
3. Actor identity is resolved and validated (if required by policy).
4. Role check is enforced (if required by policy).
5. Domain service is invoked.
6. Errors bubble up with security/business distinction.

### 7.2 Startup flow

1. Runtime bootstrap starts.
2. Credential policy preflight validates configured passwords.
3. If weak/default: raise security policy error and stop startup.
4. If strong: continue schema/bootstrap sequence.

## 8. Medium-Priority UX/Feature Design

### 8.1 Profile password-change UX

Add a password-change modal in `Profile`:
- Inputs: current password, new password, confirm new password.
- Client-side validation: non-empty, new != old, confirmation match.
- Backend call: existing `PATCH /api/v1/profile/password`.
- On success: show success toast and enforce re-login (recommended).

### 8.2 Register/Forgot Password behavior

Login page currently has placeholder links.

Replace with controlled flows:
- Register entry: explicit message "Admin accounts are created by super admin only."
- Forgot-password entry: controlled reset request path (no anonymous reset in this phase).

### 8.3 Controlled admin account creation

Introduce/clarify a super-admin-only account creation operation:
- Role assignment explicit.
- Secure initial credential handling (generated or operator-provided strong password).
- Audit log required for creation/reset operations.

## 9. Testing Strategy

### 9.1 High-priority tests

1. Route auth/authz tests (`tests/api/test_phase2_http_api_bridge.py`):
   - no actor -> denied on protected writes,
   - inactive actor -> denied,
   - wrong role -> denied,
   - allowed role -> pass.
2. Startup credential policy tests:
   - weak/default password config -> startup fail,
   - strong config -> startup success.
3. Profile safety tests (`tests/services/test_profile_service.py`):
   - missing identity -> fail for read/update/password change,
   - explicit valid identity -> pass.
4. Regression checks for services impacted by operator handling.

### 9.2 Medium-priority tests

1. Profile state/page tests for password-change flow.
2. Login page tests ensuring no placeholder `href="#"` for register/forgot-password actions.
3. Controlled account-creation permission/audit tests.

### 9.3 Verification policy

- Use explicit test selections with `-v`.
- Avoid `pytest -q` per execution constraint.

## 10. Milestones

### H1: Auth boundary and unsafe fallback removal
- Deliver centralized policy guard.
- Remove unsafe operator defaults in protected writes.
- Verify with auth/authz route tests.

### H2: Startup credential hardening
- Enforce weak-password fail-fast.
- Update bootstrap/account creation credential policy.
- Verify startup security tests.

### M1: Usability completion
- Add profile password-change UI.
- Replace login placeholder links with controlled real flows.
- Add/clarify super-admin-only account creation operation.

## 11. Acceptance Criteria

High-priority done when:
- Protected writes cannot run without valid actor identity.
- Role-restricted routes reject non-authorized roles.
- No protected write path silently defaults to `"admin"`.
- Startup fails on weak/default credentials.
- Profile operations do not fallback to super-admin implicitly.

Medium-priority done when:
- Admin can change password through UI flow.
- Login page register/forgot-password are real controlled flows, not placeholders.
- Admin account creation is controlled by super-admin policy with auditability.

## 12. Rollout and Risk Notes

- Immediate-enforcement rollout may break legacy calls/tests relying on default operator fallback; this is expected and required.
- Startup fail-fast behavior will require ops/dev to set secure credentials before runtime.
- Document environment requirements clearly to avoid deployment confusion.
