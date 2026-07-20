import os
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from bbi_os.api.v1 import router as v1_router
from bbi_os.cockpit.router import router as cockpit_router
from bbi_os.core.error_system.registry import register_exception_handlers
from bbi_os.observability import get_observability
from bbi_os.operational import get_operational_metrics, install_operational_middleware
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
    application.include_router(v1_router)
    install_operational_middleware(application)
    register_exception_handlers(application)

    @application.get("/")
    def root():
        return {"status": "running", "system": "BBIOS ACTIVE"}

    @application.get("/health")
    def health():
        return {"status": "ok"}

    @application.get("/health/ready")
    def readiness():
        data_path = settings.data_dir
        directory_to_check = data_path if data_path.exists() else data_path.parent
        data_path_accessible = directory_to_check.exists() and os.access(
            directory_to_check, os.R_OK | os.W_OK
        )
        checks = {
            "settings_loaded": True,
            "json_data_path_accessible": data_path_accessible,
            "required_directories_exist": directory_to_check.exists(),
            "startup_completed": True,
        }
        ready = all(checks.values())
        status_code = 200 if ready else 503
        return JSONResponse(
            status_code=status_code,
            content={"status": "ready" if ready else "not_ready", "checks": checks},
        )

    @application.get("/metrics")
    def metrics():
        endpoint_metrics = get_observability().metrics.snapshot()
        return {
            **get_operational_metrics().snapshot(),
            "application_version": settings.app_version,
            "endpoint_metrics": endpoint_metrics,
        }

    return application


app = create_app()
