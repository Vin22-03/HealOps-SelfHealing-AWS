from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from routers import pages, api, health

app = FastAPI(title="HealOps", version="1.0.0")

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Routers
app.include_router(pages.router)
app.include_router(api.router)
app.include_router(health.router)
app.include_router(load.router)
