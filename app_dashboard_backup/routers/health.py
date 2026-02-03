from fastapi import APIRouter
from fastapi.responses import JSONResponse
import time
from app.core.state import SIM

# ✅ THIS LINE IS MANDATORY
router = APIRouter()

@router.get("/health")
def health_check():
    # Simulated latency
    if SIM["latency_ms"] > 0:
        time.sleep(SIM["latency_ms"] / 1000)

    # Simulated failure
    if SIM["health_fail"]:
        return JSONResponse(
            status_code=500,
            content={
                "status": "unhealthy",
                "service": "healops-app",
                "reason": "SIMULATED_HEALTH_FAILURE"
            }
        )

    return {
        "status": "healthy",
        "service": "healops-app"
    }
