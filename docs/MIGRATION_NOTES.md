# Migration Notes — Security & Config Changes

This repo received a security-focused configuration and middleware update. Follow these deployment steps:

1. Provide `SECRET_KEY` in production (do not commit). Store it in your secret manager and inject at runtime.
2. Ensure `ALLOWED_HOSTS` and `ALLOWED_ORIGINS` are set to your domain(s) in production.
3. Replace the in-memory rate limiter and brute-force protections with Redis-based counters before scaling to multiple workers.
4. Ensure `STRICT_STARTUP_CHECKS=True` in production so the app fails fast on misconfiguration.
5. If you use Docker Compose, keep a host-only `.env.production` with secrets and do not commit it.
6. Review `docs/SECURITY.md` for details and next steps (password reset, audit, etc.).

