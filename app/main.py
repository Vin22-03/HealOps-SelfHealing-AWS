from fastapi import FastAPI
import time

app = FastAPI(title="HealOps Probe")

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "healops-probe",
        "timestamp": int(time.time())
    }

@app.get("/")
def root():
    return {"message": "HealOps probe running"}
