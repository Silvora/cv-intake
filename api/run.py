from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from api.routers.cv import router as cv_router
from api.routers.job import router as job_router
from api.routers.sse import router as sse_router
from api.routers.upload import router as upload_router
from config.app import appConfig

PUBLIC_DIR = Path(__file__).resolve().parents[1] / "public"




class NentWorker:
    def __init__(self):
        self.app = None
        self.setup()

    def setup(self):
        self.app = FastAPI()
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=appConfig.server.cors_origins,  # 允许的前端地址
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        self.app.include_router(job_router)
        self.app.include_router(upload_router)
        self.app.include_router(cv_router)
        self.app.include_router(sse_router)
        PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
        self.app.mount("/public", StaticFiles(directory=str(PUBLIC_DIR)), name="public")

    def run(self):
        import uvicorn

        uvicorn.run(
            self.app,
            host=appConfig.server.host,
            port=appConfig.server.port,
        )

    
