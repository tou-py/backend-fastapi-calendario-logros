import uvicorn
import asyncio
import asyncpg
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
    """Espera a que PostgreSQL esté listo antes de crear las tablas."""
    retries = 10
    while retries > 0:
        try:
            conn = await asyncpg.connect(
                user=settings.POSTGRES_USER,
                password=settings.POSTGRES_PASSWORD,
                database=settings.POSTGRES_DB,
                host=settings.POSTGRES_HOST,
                port=settings.POSTGRES_PORT,
            )
            await conn.close()
            break  # Si la conexión es exitosa, continuamos
        except Exception:
            retries -= 1
            print("Esperando a que PostgreSQL esté listo...")
            await asyncio.sleep(3)  # Espera 3 segundos antes de intentar de nuevo

    async with sessionmanager._engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn))

    yield

    await sessionmanager.close()


app = FastAPI(
    lifespan=lifespan,
    title="Calendario de Logros",
    version="0.0.1",
    summary="Una API que te ayuda a registrar y ver tus logros y actividades",
)


@app.get("/")
def root():
    return {"message": "La API funciona correctamente :)"}


app.include_router(users_router)
app.include_router(activities_router)
app.include_router(activity_types_router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", reload=True, port=8000)
