# Email Verification Design

## Summary

Add email verification to the registration flow with a soft gate: unverified users can browse (read endpoints) but cannot perform write operations (create monitors, acknowledge alerts, etc.).

## Decisions

- **Token method**: Signed JWT with `type: "email_verify"`, 24h expiry. No DB token column needed.
- **Verification flow**: Backend `GET /auth/verify-email?token=xxx` validates and redirects to frontend `/login?verified=true`.
- **Gate enforcement**: FastAPI dependency `require_verified_user` applied to write endpoints. Returns 403 for unverified users.
- **Email delivery**: SendGrid (existing infrastructure), dispatched via Celery task after registration.

## Database Changes

Add to `users` table:
- `is_email_verified: bool, default=False`
- `email_verified_at: datetime, nullable`

## New Endpoints

| Endpoint | Method | Auth | Purpose |
|---|---|---|---|
| `/auth/verify-email?token=` | GET | None | Validate token, mark verified, redirect to frontend |
| `/auth/resend-verification` | POST | Bearer | Re-send verification email, rate-limited 1/2min |

## Soft Gate Rules

**Gated (403 if unverified):**
- POST/PATCH/DELETE `/monitors/*`
- POST `/monitors/{id}/scrape`
- PATCH `/alerts/{id}/acknowledge`
- PUT `/notifications/settings/{channel}`
- POST `/notifications/test/{channel}`

**Open (unverified OK):**
- All GET endpoints
- GET/PATCH `/users/me`
- POST `/auth/resend-verification`

## Frontend Changes

- Persistent banner in AppLayout for unverified users with resend button
- Login page shows success toast when `?verified=true`
- Write action buttons disabled with tooltip for unverified users
- `UserRead` schema includes `is_email_verified`

## Config Additions

- `frontend_url: str = "http://localhost:5173"`
- `email_verification_token_expire_hours: int = 24`
