# Forget Password Development Plan

## Phases 1-4: Frontend UI Design
1. **Phase 1 – Entry Point & Navigation**: Add a "Forgot password" link to the existing sign-in page. When clicked, it routes to the new standalone Forget Password page (no modal) so the flow stays focused on email input.
2. **Phase 2 – Email Capture Screen**: Build the Forget Password page with a single email input field (type="email") and a submit button. Include inline validation (required + valid format) and a status message area for success or error feedback. Disable the submit button until the email passes validation.
3. **Phase 3 – Confirmation & Email Trigger**: After the user submits, show a message that a reset link was sent when the backend successfully queues the email; explicitly mention that the backend is sending the reset email to the targeted address, and offer a link back to sign-in. Handle loading and error states (e.g., network failure, unknown email) with contextual text.
4. **Phase 4 – Reset Password Page UI**: Design the reset-password landing page (opened via email link) with two password inputs ("New Password" and "Confirm Password"), strength hints, and client-side validation that the values match. Add a submit button and visual cue when the passwords differ.

## Phases 5-8: Backend Implementation
5. **Phase 5 – Request Endpoint**: Create or extend an API endpoint that accepts the email, verifies the account exists, generates a time-limited token, stores it (with expiry), and sends a single-use reset link via email. Log attempts for auditing.
6. **Phase 6 – Token Validation Middleware**: Implement backend logic that validates the reset token when the user visits the reset-password page (e.g., token exists, not expired/revoked) before allowing password updates.
7. **Phase 7 – Password Update Handling**: Build the endpoint that accepts the new password payload, checks that the token is valid, hashes the new credential, updates the user record, and invalidates the token. Return clear success/failure states.
8. **Phase 8 – Notifications & UX Hooks**: Trigger email notifications for both the reset link dispatch and confirmation once the password changes; surface any backend errors back to the UI (expired token, rate limits) so the front end can guide the user.

## Phase 9: Security Checks
- Validate all inputs server-side (email, password, token) and enforce strong password policy.
- Ensure reset tokens are single-use, time-limited, and stored securely (hashed if stored in DB).
- Rate-limit reset requests per IP/email and monitor logs for repeated failures to mitigate abuse.
- Include audit logging for password resets and consider alerting/support escalation when multiple resets occur in a short window.
