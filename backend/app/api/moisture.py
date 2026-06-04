from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Integer, desc, func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Bed, MoistureReading
from app.schemas import MoistureReadingRead, MoistureSeriesPoint
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


@router.get("/beds/{bed_id}/moisture/series", response_model=list[MoistureSeriesPoint])
def moisture_series(
    bed_id: int,
    range: str = Query(default="24h", pattern="^(6h|24h|today)$"),
    bucket: str = Query(default="1m", pattern="^(1m|5m)$"),
    db: Session = Depends(get_db),
) -> list[MoistureSeriesPoint]:
    if db.get(Bed, bed_id) is None:
        raise HTTPException(status_code=404, detail="Beet wurde nicht gefunden")
    now = datetime.utcnow()
    if range == "today":
        start = datetime.combine(now.date(), datetime.min.time())
    else:
        hours = 6 if range == "6h" else 24
        start = now - timedelta(hours=hours)
    bucket_seconds = 300 if bucket == "5m" else 60
    bucket_expr = (func.strftime("%s", MoistureReading.created_at) / bucket_seconds).cast(Integer) * bucket_seconds
    rows = db.execute(
        select(
            bucket_expr.label("bucket_ts"),
            func.avg(MoistureReading.moisture_percent),
            func.avg(MoistureReading.raw_value),
        )
        .where(
            MoistureReading.bed_id == bed_id,
            MoistureReading.created_at >= start,
            MoistureReading.is_valid.is_(True),
        )
        .group_by(bucket_expr)
        .order_by(bucket_expr)
    ).all()
    return [
        MoistureSeriesPoint(
            timestamp=datetime.utcfromtimestamp(int(row[0])),
            avg_moisture_percent=round(row[1], 1) if row[1] is not None else None,
            avg_raw_value=round(row[2], 1) if row[2] is not None else None,
        )
        for row in rows
    ]
