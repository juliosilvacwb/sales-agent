import os
from typing import Any, Callable
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from src.adapter.inbound.web.chat_controller import router as chat_router

load_dotenv()

app = FastAPI(
    title="Sales Data Analysis API",
    description="API for the Sales Data Analysis Agent Web Chat Interface",
    version="1.0.0",
)


# HTTP Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next: Callable[[Request], Any]) -> Any:
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# CORS configuration
raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:8000,http://127.0.0.1:8000,http://localhost:3000",
)
allowed_origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)

# Mount static files directory
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.post("/auth/login")
def auth_login_proxy(request: dict) -> Any:
    """Proxy authentication requests to the configured Auth Microservice."""
    import json
    import urllib.request
    import urllib.error
    from fastapi import HTTPException, status

    auth_service_url = os.getenv("AUTH_SERVICE_URL", "http://localhost:8001").rstrip("/")
    target_url = f"{auth_service_url}/auth/login"
    payload = json.dumps(request).encode("utf-8")
    req = urllib.request.Request(
        target_url,
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            body = response.read().decode("utf-8")
            return json.loads(body)
    except urllib.error.HTTPError as err:
        error_body = err.read().decode("utf-8")
        try:
            err_json = json.loads(error_body)
            detail = err_json.get("detail", "Credenciais inválidas")
        except Exception:
            detail = "Credenciais inválidas"
        raise HTTPException(status_code=err.code, detail=detail)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Não foi possível conectar ao serviço de autenticação ({auth_service_url}): {exc}",
        )


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def root_redirect() -> RedirectResponse:
    return RedirectResponse(url="/static/index.html")
