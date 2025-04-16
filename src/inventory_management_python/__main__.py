from fastapi import FastAPI
from uvicorn import run

from inventory_management_python.routes import router as api_router

app = FastAPI()

app.include_router(api_router, prefix="/api")


def main():
    run(app)
