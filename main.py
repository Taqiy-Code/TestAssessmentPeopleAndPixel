from fastapi import FastAPI
import uvicorn as uv 

app = FastAPI(
    title="Media Monitoring API",
    version=1
)

def main():
    uv.run(app, host="127.0.0.1", port=8000, reload=True)

if __name__ == "__main__":
    main()
