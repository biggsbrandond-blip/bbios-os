from fastapi import FastAPI

# KEEP YOUR EXISTING SYSTEM
from bbi_os.cockpit.router import router as cockpit_router
from bbi_os.settings import get_settings


def create_app():
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="BBIOS Unified System",
        debug=settings.debug,
    )

    # CORE SYSTEM
    app.include_router(cockpit_router, prefix=settings.api_prefix)

    @app.get("/")
    def root():
        return {"status": "running", "system": "BBIOS ACTIVE"}

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()
