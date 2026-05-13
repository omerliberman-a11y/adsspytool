from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from adspy.api.routes import ads as ads_routes
from adspy.config import get_settings
from adspy.utils.logging import configure_logging


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(level=settings.log_level, json=settings.log_json)
    yield


app = FastAPI(title="adspy", version="0.1.0", lifespan=lifespan)
app.include_router(ads_routes.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
