# Refresh sessions

Migration 006 adds persistent refresh sessions. Existing refresh tokens do not have a session ID and cannot be refreshed after migration; users must sign in again. Each successful refresh rotates the session's token ID atomically, so a previously used refresh token cannot be reused. Logout removes the corresponding session even if it receives an older, unexpired token from that session.

Logout clears the browser cookies and revokes the refresh session. Access tokens already issued remain valid until their configured expiry. Expired refresh-session records are removed the next time that user signs in, or when the user is deleted.

Downgrading the application to a version that accepts stateless refresh tokens can make previously revoked, unexpired legacy refresh tokens usable again. Coordinate a JWT signing-key rotation with any rollback if those tokens must remain invalid.
