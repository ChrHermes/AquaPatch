from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Bed, MoistureReading
from app.schemas import MoistureReadingRead
from app.services.registry import moisture_service

router = APIRouter(prefix="/api", tags=["moisture"])


@router.get("/beds/{bed_id}/moisture", response_model=MoistureReadingRead)
def read_bed_moisture(bed_id: int, db: Session = Depends(get_db)) -> MoistureReading:
    bed = db.get(Bed, bed_id)
    if bed is None:
        raise HTTPException(status_code=404, detail="Beet wurde nicht gefunden")
    return moisture_service.read_and_store(db, bed)


@router.get("/readings/latest", response_model=list[MoistureReadingRead])
def latest_readings(db: Session = Depends(get_db)) -> list[MoistureReading]:
    readings: list[MoistureReading] = []
    beds = db.scalars(select(Bed).order_by(Bed.id)).all()
    for bed in beds:
        reading = db.scalars(
            select(MoistureReading)
            .where(MoistureReading.bed_id == bed.id)
            .order_by(desc(MoistureReading.created_at))
            .limit(1)
        ).first()
        if reading:
            readings.append(reading)
    return readings


@router.get("/readings", response_model=list[MoistureReadingRead])
def list_readings(
    bed_id: int | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[MoistureReading]:
    statement = select(MoistureReading).order_by(desc(MoistureReading.created_at)).limit(limit)
    if bed_id is not None:
        statement = statement.where(MoistureReading.bed_id == bed_id)
    return list(db.scalars(statement).all())
