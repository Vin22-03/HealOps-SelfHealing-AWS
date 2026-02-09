from fastapi import APIRouter

router = APIRouter(prefix="/inject")

@router.get("/crash")
def crash_app():
    """
    This intentionally crashes the container.
    ECS will treat this as an essential container exit → task STOPPED → auto-heal.
    """
    raise RuntimeError("Simulated container crash for HealOps testing")

