from fastapi import FastAPI
from bbi_os.cockpit.handler import CockpitApiHandler
from bbi_os.cockpit.router import router
from bbi_os.settings import get_settings

settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
)

app.include_router(router, prefix=settings.api_prefix)
