from fastapi import FastAPI

from bbi_os.cockpit.router import router as cockpit_router
from bbi_os.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="BBIOS Unified System",
        debug=settings.debug,
    )

    application.include_router(cockpit_router, prefix=settings.api_prefix)

    @application.get("/")
    def root():
        return {"status": "running", "system": "BBIOS ACTIVE"}

    @application.get("/health")
    def health():
        return {"status": "ok"}

    return application


app = create_app()
