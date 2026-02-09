from fastapi import APIRouter
import os
import signal

router = APIRouter(prefix="/inject")

@router.get("/crash")
def crash_app():
    os.kill(os.getpid(), signal.SIGKILL)   # 💥 force container OUT
    return {"status": "should never reach here"}
