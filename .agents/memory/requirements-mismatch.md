---
name: Requirements mismatch
description: Imported project declared Flask dependencies but actually runs FastAPI.
---

# Requirements mismatch

**Rule:** When importing an external project, verify the declared dependencies against the actual imports and framework used before installing.

**Why:** The imported `requirements.txt` listed Flask, flask-cors, and gunicorn, but the application code is FastAPI + Uvicorn. Blindly installing the file would leave the app unable to start.

**How to apply:**
- Read `app/main.py` and the API routers to identify the real framework.
- Replace incorrect requirements with the correct packages (FastAPI, Uvicorn, plus the actual runtime deps).
- Add missing transitive deps surfaced at runtime (e.g., `python-multipart` for FastAPI form data).
- Keep the existing project structure; do not migrate to a different framework unless requested.
