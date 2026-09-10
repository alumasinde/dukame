"""Rate limit constants and utilities for sensitive endpoints."""

# Authentication endpoints (per email, 5 attempts per 10 minutes)
AUTH_LOGIN_LIMIT = 5
AUTH_LOGIN_WINDOW = 600  # seconds

# Email verification/password reset (per email, 3 attempts per 30 minutes)
AUTH_EMAIL_LIMIT = 3
AUTH_EMAIL_WINDOW = 1800  # seconds

# Registration (per IP, 10 new accounts per 24 hours)
AUTH_REGISTER_LIMIT = 10
AUTH_REGISTER_WINDOW = 86400  # seconds
