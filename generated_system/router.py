
from fastapi import APIRouter
from bbi_os.cockpit.service import CockpitService

router = APIRouter()
service = CockpitService()



@router.get("/")
def endpoint():
    return {"status": "health_check"}


@router.get("/health")
def endpoint():
    return {"status": "system_health"}


@router.post("/create-client")
def endpoint():
    return {"status": "generic"}


@router.post("/test-pipeline")
def endpoint():
    return {"status": "execution_test"}

