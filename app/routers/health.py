from fastapi import APIRouter, Response
import os

router = APIRouter(prefix="/health")

SIMULATE_FAIL = os.getenv("SIMULATE_FAIL", "false")

@router.get("")
def health_check():
    if SIMULATE_FAIL.lower() == "true":
        return Response(status_code=500)

    return {"status": "healthy", "service": "healops-ui"}
