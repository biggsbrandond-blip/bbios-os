from fastapi import FastAPI
from bbi_os.cockpit.router import router

app = FastAPI(
    title="BBIOS OS",
    version="1.0"
)

app.include_router(router, prefix="/cockpit")
