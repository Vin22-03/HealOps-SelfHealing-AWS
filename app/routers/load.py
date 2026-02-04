import time
from fastapi import APIRouter, Query

router = APIRouter()

@router.get("/burn-cpu")
def burn_cpu(seconds: int = Query(30, ge=5, le=120)):
    """
    Intentionally burn CPU for testing auto-scaling and self-healing.
    Safe, bounded, and controlled.
    """
    end_time = time.time() + seconds
    x = 0
    while time.time() < end_time:
        x += 1  # busy loop to consume CPU

    return {
        "status": "completed",
        "burn_seconds": seconds,
        "note": "CPU burn finished successfully"
    }
