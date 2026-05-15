import uvicorn
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import config
from api.database import db
from api.routers import boards, columns, tasks, activities, sync, dashboard, history, disciplines


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.connect()
    yield
    db.close()


app = FastAPI(
    title="StudyBoard API — UNISALESIANO",
    description="Backend do sistema de estudos com Kanban acadêmico integrado ao monitor Moodle",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(boards.router)
app.include_router(columns.router)
app.include_router(tasks.router)
app.include_router(activities.router)
app.include_router(sync.router)
app.include_router(dashboard.router)
app.include_router(history.router)
app.include_router(disciplines.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "study_db": config.study_db_path}


if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host=config.host,
        port=config.port,
        reload=config.debug,
    )
