from fastapi import APIRouter
from pydantic import BaseModel
from bbi_os.cockpit.service import CockpitService

router = APIRouter()
service = CockpitService()


# -------------------------
# REQUEST MODEL
# -------------------------
class ClientRequest(BaseModel):
    client_name: str
    plan: str


# -------------------------
# CREATE CLIENT
# -------------------------
@router.post("/create-client")
def create_client(payload: ClientRequest):
    return service.create_client(payload.client_name, payload.plan)


# -------------------------
# GET CLIENT BY ID
# -------------------------
@router.get("/client/{client_id}")
def get_client(client_id: str):
    return service.get_client(client_id)


# -------------------------
# SEARCH CLIENTS
# -------------------------
@router.get("/clients/search")
def search_clients(name: str = "", plan: str = ""):
    return service.search_clients(name, plan)


# -------------------------
# TEST PIPELINE
# -------------------------
@router.post("/test-pipeline")
def test_pipeline():
    return service.test_pipeline()
