from pathlib import Path
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
import uvicorn
from app.routes import frete_routes, produto_routes, usuario_routes, vendedor_routes

ENABLE_API_DOCS = os.getenv("ENABLE_API_DOCS", "false").strip().lower() == "true"
ENABLE_NGROK = os.getenv("ENABLE_NGROK", "false").strip().lower() == "true"

NGROK_HOST_PATTERNS = [
    "*.ngrok-free.app",
    "*.ngrok.app",
    "*.ngrok.io",
    "*.ngrok-free.dev",
    "*.ngrok.dev",
]
NGROK_ORIGIN_REGEX = (
    r"https://([a-zA-Z0-9-]+\.)?(ngrok-free\.app|ngrok\.app|ngrok\.io|ngrok-free\.dev|ngrok\.dev)$"
)

app = FastAPI(
    title="China/CSSBuy CRUD",
    docs_url="/docs" if ENABLE_API_DOCS else None,
    redoc_url="/redoc" if ENABLE_API_DOCS else None,
    openapi_url="/openapi.json" if ENABLE_API_DOCS else None,
)

allowed_hosts = [
    host.strip()
    for host in os.getenv("ALLOWED_HOSTS", "phcgv-import.vercel.app,127.0.0.1,localhost").split(",")
    if host.strip()
]
if ENABLE_NGROK:
    for host_pattern in NGROK_HOST_PATTERNS:
        if host_pattern not in allowed_hosts:
            allowed_hosts.append(host_pattern)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=allowed_hosts or ["phcgv-import.vercel.app", "127.0.0.1", "localhost"],
)

allowed_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]
allow_origin_regex = NGROK_ORIGIN_REGEX if ENABLE_NGROK else None

if allowed_origins or allow_origin_regex:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_origin_regex=allow_origin_regex,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIST_DIR = BASE_DIR / "frontend" / "dist"
FRONTEND_ASSETS_DIR = FRONTEND_DIST_DIR / "assets"
FRONTEND_INDEX_FILE = FRONTEND_DIST_DIR / "index.html"

if FRONTEND_ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_ASSETS_DIR), name="assets")

app.include_router(produto_routes.router)
app.include_router(frete_routes.router)
app.include_router(usuario_routes.router)
app.include_router(vendedor_routes.router)


@app.middleware("http")
async def add_security_headers(request, call_next):
    """Cabeçalhos básicos de hardening em todas as respostas."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    return response


@app.get("/")
def home() -> FileResponse:
    """Serve a página principal do frontend.

    Returns:
        FileResponse: Arquivo HTML inicial da aplicação.
    """
    if FRONTEND_INDEX_FILE.exists():
        return FileResponse(FRONTEND_INDEX_FILE)

    return JSONResponse({
        "status": "ok",
        "message": "API online. Frontend nao empacotado neste backend.",
    })


@app.get("/reset-password")
def reset_password_page() -> FileResponse:
    """Serve a SPA para fluxo de redefinição de senha por token."""
    if FRONTEND_INDEX_FILE.exists():
        return FileResponse(FRONTEND_INDEX_FILE)

    raise HTTPException(
        status_code=404,
        detail="Frontend de reset-password nao esta disponivel neste backend.",
    )


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8050)