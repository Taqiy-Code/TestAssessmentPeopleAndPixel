from fastapi import FastAPI
import uvicorn as uv 

from app.routers import router

app = FastAPI(
    title="Media Monitoring API",
    version="1.0.0",
)

app.include_router(router)

def main():
    uv.run("app.main:app", host="127.0.0.1", port=8000, reload=True)

if __name__ == "__main__":
    main()
