---
name: PIN persistence
description: How the login PIN is stored and why it changed from env-only to database-backed.
---

# PIN persistence

**Rule:** PIN changes made through the `/api/auth/change-pin` endpoint must survive server restarts.

**Why:** The original implementation only held the PIN in memory or read it from `BANCO_LINKS_PIN`. After a restart, a changed PIN reverted to the default (`1234`), which is a silent security regression and locks users out of their own data.

**How to apply:**
- Store the active PIN in a `Config` table row keyed by `auth_pin`.
- On startup, resolve the PIN in this order: `BANCO_LINKS_PIN` env/secret → `config.auth_pin` in DB → default `1234`.
- When the PIN changes, invalidate existing in-memory sessions by clearing the session store.
- Relevant models: `app/models.py` (`Config` table), helpers: `app/database.py` (`get_config`, `set_config`), logic: `app/api/auth.py`.
