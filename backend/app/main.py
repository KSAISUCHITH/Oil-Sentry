from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.alerts import router as alerts_router
from app.api.rag import router as rag_router
from app.api.reports import router as reports_router
from app.api.risk import router as risk_router
from app.api.similarity import router as similarity_router
from app.api.websocket import router as websocket_router
from app.api.intelligence import router as intelligence_router
from app.api.wells import router as wells_router
from app.core.config import settings
from app.core.database import Base, engine, get_db
from app import models

app = FastAPI(title="eRTMAC-NWIS API")
app.add_middleware(
	CORSMiddleware,
	allow_origins=[settings.frontend_url],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

app.include_router(wells_router, prefix="/api")
app.include_router(alerts_router, prefix="/api")
app.include_router(reports_router, prefix="/api")
app.include_router(similarity_router, prefix="/api")
app.include_router(risk_router, prefix="/api")
app.include_router(rag_router, prefix="/api")
app.include_router(intelligence_router, prefix="/api")
app.include_router(websocket_router)



@app.on_event("startup")
def create_tables() -> None:
	if engine is not None:
		with engine.begin() as connection:
			connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
		try:
			with engine.begin() as connection:
				connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
		except Exception:
			# pgvector is optional for this phase and is not installed on the current server.
			pass
		Base.metadata.create_all(bind=engine)


@app.get("/")
def root() -> dict[str, str]:
	return {"message": "NWIS API is running"}


@app.get("/health")
def health() -> dict[str, str]:
	return {"status": "healthy"}


@app.get("/db-test")
def database_test(database: Session = Depends(get_db)) -> dict[str, str]:
	try:
		database.execute(text("SELECT 1"))
		return {"database": "connected"}
	except Exception as exc:
		raise HTTPException(status_code=500, detail=f"Database connection failed: {exc}") from exc
