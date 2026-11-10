from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import (
    analytics,
    assets,
    audit,
    auth,
    facts,
    guidelines,
    organisations,
    profile,
    reviews,
    settings as settings_router,
    sources,
    submissions,
    terminology,
)

settings = get_settings()

app = FastAPI(
    title="BrandProof AI API",
    version="0.1.0",
    description="Evidence-based brand governance platform. Verify. Explain. Improve. Human approval.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "app": settings.app_name, "environment": settings.environment}


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


app.include_router(auth.router)
app.include_router(organisations.router)
app.include_router(profile.router)
app.include_router(facts.router)
app.include_router(terminology.router)
app.include_router(guidelines.router)
app.include_router(sources.router)
app.include_router(assets.router)
app.include_router(audit.router)
app.include_router(submissions.router)
app.include_router(reviews.router)
app.include_router(analytics.router)
app.include_router(settings_router.router)
