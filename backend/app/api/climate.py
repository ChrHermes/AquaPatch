from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import ClimateReading
from app.schemas import ClimateReadingRead
from app.services.registry import climate_service

router = APIRouter(prefix="/api/climate", tags=["climate"])


@router.get("/latest", response_model=ClimateReadingRead)
def latest_climate(db: Session = Depends(get_db)) -> ClimateReading:
    return climate_service.latest_or_read(db)


@router.get("/readings", response_model=list[ClimateReadingRead])
def list_climate_readings(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[ClimateReading]:
    return list(db.scalars(select(ClimateReading).order_by(desc(ClimateReading.created_at)).limit(limit)).all())


@router.post("/read", response_model=ClimateReadingRead)
def read_climate(db: Session = Depends(get_db)) -> ClimateReading:
    return climate_service.read_and_store(db)
