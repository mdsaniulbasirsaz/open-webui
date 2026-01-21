# Development Plan: Email Verification OTP + Link

## Objective
Deliver a complete OTP + link email verification flow, aligned with `explore-architecture/PlanningEmailVerificationOTPWithLink.md`, and show a verified success page that includes a Pricing Plan CTA button after link verification.

## Phase 1: Backend Foundations
### Scope
Add link-token storage and verification logic while keeping OTP behavior intact.

### Work Items
- Extend verification data model with link token hash, expiry, and used-at fields.
- Generate a verification link token alongside OTP on signup.
- Implement/extend link verification endpoint:
  - `GET /api/auth/verify-email/link`
  - Validate token hash, TTL, and unused status.
  - Mark email verified and invalidate OTP + link on success.
- Update resend behavior to regenerate OTP + link and invalidate prior tokens.
- Keep error responses generic to avoid email existence leakage.

### Deliverables
- Link token fields in storage.
- Link verification endpoint.
- Resend regenerates both OTP + link.

## Phase 2: Email + Config
### Scope
Send both OTP and link in the verification email and expose configuration.

### Work Items
- Update verification email template to include:
  - OTP code.
  - Single-use verification link.
- Add/confirm config flags:
  - `ENABLE_EMAIL_VERIFICATION_LINK`
  - `EMAIL_VERIFICATION_LINK_TTL` (default to OTP TTL)
  - Existing resend cooldown and OTP TTL retained.
- Add documentation for new flags and behavior in ops notes.

### Deliverables
- OTP + link sent in the same email.
- Config documented and wired.

## Phase 3: Frontend + Tests
### Scope
Handle verification links on the frontend, show a post-verify success page with a Pricing Plan CTA, and validate end-to-end behavior.

### Work Items
- Frontend:
  - Parse `token` + `email` from verification link.
  - Call link verification endpoint.
  - On success, render a verification success page (not just a toast) with a primary "View Pricing Plans" button.
  - Button redirects to `/pricing` (new route that renders the existing pricing UI in `src/lib/components/layout/Overlay/AccountPending.svelte`).
  - Preserve existing OTP entry UI.
- Tests:
  - OTP verify success invalidates link.
  - Link verify success invalidates OTP.
  - Resend invalidates old tokens.
  - Expired token rejected.
  - Rate limit responses are enforced.

### Deliverables
- Link verification UX in auth route.
- Tests covering OTP + link flows.

## Acceptance Criteria
- Either OTP or link verifies the email successfully.
- Verification is single-use and respects TTL.
- Resend issues fresh OTP + link and invalidates old ones.
- No sensitive information is exposed in error responses.
- Link verification success renders a dedicated success page with a Pricing Plan CTA and redirect.

## Open Decisions
- Decision: redirect to sign-in after link verification success page (no auto-login).
- Link TTL same as OTP TTL or longer?
- Require `email` param in link or derive from token only?
