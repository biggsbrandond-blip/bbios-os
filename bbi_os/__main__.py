from fastapi import FastAPI

# KEEP YOUR EXISTING SYSTEM
from bbi_os.cockpit.router import router as cockpit_router


def create_app():
    app = FastAPI(
        title="BBIOS OS",
        version="1.0",
        description="BBIOS Unified System"
    )

    # CORE SYSTEM
    app.include_router(cockpit_router, prefix="/cockpit")

    @app.get("/")
    def root():
        return {"status": "running", "system": "BBIOS ACTIVE"}

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()
