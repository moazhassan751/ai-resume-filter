# Security Hardening Checklist (TalentLens AI)

This document summarizes the runtime and configuration improvements applied and next steps to keep the app secure.

## Changes applied
- `app/core/config.py`: stricter defaults, `SECRET_KEY` must be provided in production, `ALLOWED_ORIGINS` and `ALLOWED_HOSTS` separation, `STRICT_STARTUP_CHECKS` option.
- `app/main.py`: added `TrustedHostMiddleware`, secure headers middleware, and a simple rate limiter.
- `app/services/auth_service.py`: access + refresh token helpers, expiry configuration bound to settings.
- `app/api/v1/auth.py`: login flow now issues access + refresh tokens and includes simple brute-force protection.
- `app/services/bruteforce.py`: lightweight in-memory brute-force tracker (replace with Redis for production).
- `app/services/document_service.py`: upload validation (size, extension, basic magic checks) and safer temp-then-move storage.
- `app/api/v1/data.py`: upload endpoint uses validation and `settings.UPLOAD_DIR`.

## Recommended operational practices
1. Do NOT commit secrets (`SECRET_KEY`, API keys). Use Secret Manager or CI/CD secrets.
2. Rotate `SECRET_KEY` and API keys immediately if exposed. Purge git history if leaked.
3. Use Redis-based rate limiting and brute-force counters in production (multiple workers).
4. Front your app with a TLS-terminating proxy (NGINX/ALB) and set TLS headers there.
5. Run malware/AV scanning on user uploads (e.g., ClamAV) before storing permanently.
6. Implement an audit log sink (append-only) that records authentication events and uploads.

## Password reset (placeholder)
Design:
- POST `/auth/password-reset-request` — accept email, create time-limited reset token stored in DB, send email with link.
- POST `/auth/password-reset` — accepts token + new password, validates and updates hashed password.

## Next work (high priority)
- Replace in-memory rate limiting and brute-force protection with Redis.
- Add refresh token revocation storage (DB) to allow logout and immediate revocation.
- Add Content Security Policy and tighter CSP rules for the frontend.
- Add Sentry/monitoring and secure audit log storage.

