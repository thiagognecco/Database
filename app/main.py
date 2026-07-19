"""FastAPI application for Banco de Links."""
import os
import socket
import webbrowser
from pathlib import Path
from threading import Timer
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import uvicorn

# Load environment variables
load_dotenv()

# Initialize database
from app.database import init_db, setup_auto_backup
init_db()
setup_auto_backup()

# Create FastAPI app
app = FastAPI(title="Banco de Links")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent / "static"

# Health check
@app.get("/api/health")
def health():
    """Health check endpoint"""
    return {"status": "ok"}

# Import API routes
print("[INIT] Importando rotas...")
from app.api import filters, links, search, import_export, metadata
from app.api import stats, sharing, google_drive, auth, github_backup, populate, ai

# Include routers
app.include_router(filters.router)
print("[INIT] [OK] filters.router")
app.include_router(links.router)
print("[INIT] [OK] links.router")
app.include_router(search.router)
print("[INIT] [OK] search.router")
app.include_router(import_export.router)
print("[INIT] [OK] import_export.router")
app.include_router(metadata.router)
print("[INIT] [OK] metadata.router")
app.include_router(stats.router)
print("[INIT] [OK] stats.router")
app.include_router(sharing.router)
print("[INIT] [OK] sharing.router")
app.include_router(google_drive.router)
print("[INIT] [OK] google_drive.router")
app.include_router(github_backup.router)
print("[INIT] [OK] github_backup.router")
app.include_router(auth.router)
print("[INIT] [OK] auth.router")
app.include_router(populate.router)
print("[INIT] [OK] populate.router")
app.include_router(ai.router)
print("[INIT] [OK] ai.router")

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
async def index():
    """Serve index.html"""
    return FileResponse(STATIC_DIR / "index.html")


def open_browser(url: str):
    """Open browser after a short delay to ensure server is ready."""
    try:
        webbrowser.open(url)
    except:
        pass


def get_local_ip():
    """Get local IP address for Wi-Fi access."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return "127.0.0.1"


if __name__ == "__main__":
    port = int(os.getenv("BANCO_LINKS_PORT", "8765"))
    host = "0.0.0.0"

    local_ip = get_local_ip()
    local_url = f"http://localhost:{port}"
    network_url = f"http://{local_ip}:{port}"

    print(f"\n{'='*60}")
    print(f"  Banco de Links")
    print(f"{'='*60}")
    print(f"  Local:  {local_url}")
    print(f"  Rede:   {network_url}")
    print(f"{'='*60}\n")

    Timer(2, lambda: open_browser(local_url)).start()

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
    )
