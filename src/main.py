import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.config import settings
from src.database import sessionmanager
from src.models.models import Base
from src.api.v1.endpoints.auth import router as users_router
from src.api.v1.endpoints.activities import router as activities_router
from src.api.v1.endpoints.activity_type import router as activity_types_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Crea las tablas en la base de datos al iniciar la app."""
    async with sessionmanager._engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)  # Crea las tablas

    yield

    if sessionmanager._engine is not None:
        await sessionmanager.close()


app = FastAPI(lifespan=lifespan)


@app.get("/")
def root():
    return {"message": "La API funciona correctamente :)"}


app.include_router(users_router)
app.include_router(activities_router)
app.include_router(activity_types_router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", reload=True, port=8000)
