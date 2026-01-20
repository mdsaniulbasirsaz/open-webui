## Plan: Signup Email Verification (OTP)

1. Add configuration for OTP verification and SMTP in `env.py` and `config.py`, and expose a feature flag in the frontend config payload so the UI can react when verification is required.
2. Create a new `email_verification` table (Alembic migration + model) to store OTP hashes, expiry, resend cooldowns, attempts remaining, and the intended post-verify role.
3. Implement email utility helpers: OTP generation, hashing, and SMTP send (TLS/SSL support) using a reusable HTML template.
4. Update signup flow to:
   - Create user with `pending` role when verification is required.
   - Create OTP record, send email, and return a `requires_email_verification` response without issuing a session.
5. Add endpoints to verify OTP and resend OTP, enforcing TTL, cooldown, and max attempts. On successful verification, promote the user to the intended role and return a session token.
6. Update signin to block unverified users with a clear error message and an option to resend OTP.
7. Update frontend auth page to show OTP input + resend flow when signup returns `requires_email_verification`.
