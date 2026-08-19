import uvicorn as uv 

from fastapi import FastAPI
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from pydantic import ValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from app.routers import router
from app.db import create_pool

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        app.state.pool = await create_pool()
    except Exception as e:
        print(f"Warning: Failed to connect to database on startup: {e}")
        app.state.pool = None
    yield
    if getattr(app.state, "pool", None):
        await app.state.pool.close()

app = FastAPI(
    title="Media Monitoring API",
    version="1.0.0",
    lifespan=lifespan
)

@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc: ValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": jsonable_encoder(exc.errors())},
    )

app.include_router(router)

def main():
    uv.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    main()
