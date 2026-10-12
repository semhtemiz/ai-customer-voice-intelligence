from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from .security import SecurityMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .config import Settings
from .db import database_ready
from .routes import router


class HealthResponse(BaseModel):
    status: str
    database_ready: bool


def create_app(settings: Settings | None = None):
    config = settings or Settings.from_env()
    app = FastAPI(title="Customer Voice Intelligence API", version="0.2.0")
    app.state.settings = config
    app.add_middleware(
        CORSMiddleware, allow_origins=list(config.cors_origins),
        allow_methods=["GET", "POST"], allow_headers=["Content-Type"],
    )

    @app.get("/health", response_model=HealthResponse, responses={503: {"model": HealthResponse}})
    def health():
        ready = database_ready(config.database_path)
        return JSONResponse(status_code=200 if ready else 503, content={
            "status": "ok" if ready else "unavailable", "database_ready": ready,
        })

    app.add_middleware(SecurityMiddleware, origins=config.cors_origins, hosts=config.allowed_hosts)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(config.allowed_hosts))
    app.include_router(router)
    return app


app = create_app()
