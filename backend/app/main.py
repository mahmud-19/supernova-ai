from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.routers import auth, cases
from app.seed import seed_demo_users


settings = get_settings()
app = FastAPI(title="SuperNova AI API", version="0.1.0")
cors_origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Refreshed-Token"],
)


@app.middleware("http")
async def attach_refreshed_token(request: Request, call_next):
    response = await call_next(request)
    refreshed = getattr(request.state, "refreshed_token", None)
    if refreshed:
        response.headers["X-Refreshed-Token"] = refreshed
    return response


@app.on_event("startup")
def startup() -> None:
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_demo_users(db)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auth.router, prefix="/api")
app.include_router(cases.router, prefix="/api")
