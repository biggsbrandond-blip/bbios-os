
from fastapi import FastAPI
from bbi_os.cockpit.router import router

app = FastAPI(
    title="BBIOS Cockpit System Template",
    version="0.1"
)

app.include_router(router, prefix="/cockpit")
