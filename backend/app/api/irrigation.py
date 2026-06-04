from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Bed, IrrigationRun
from app.schemas import IrrigationCurrent, IrrigationInterval, IrrigationRunRead, WaterRequest
from app.services.registry import irrigation_service

router = APIRouter(prefix="/api", tags=["irrigation"])


@router.post("/beds/{bed_id}/water", response_model=IrrigationRunRead)
async def water_bed(bed_id: int, payload: WaterRequest | None = None, db: Session = Depends(get_db)) -> IrrigationRun:
    request = payload or WaterRequest()
    try:
        return await irrigation_service.water_bed(
            db,
            bed_id=bed_id,
            duration_seconds=request.duration_seconds,
            trigger=request.trigger,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404 if "gefunden" in str(exc) else 400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/beds/{bed_id}/water/stop")
async def stop_bed_water(bed_id: int) -> dict[str, object]:
    stopped = irrigation_service.stop_bed(bed_id)
    if not stopped:
        raise HTTPException(status_code=404, detail="Für dieses Beet läuft keine Bewässerung")
    return {"stopped": True, "message": "Bewässerung abgebrochen"}


@router.post("/irrigation/current/stop")
async def stop_current_water() -> dict[str, object]:
    stopped = irrigation_service.stop_current()
    if not stopped:
        raise HTTPException(status_code=404, detail="Es läuft keine Bewässerung")
    return {"stopped": True, "message": "Bewässerung abgebrochen"}


@router.get("/irrigation/current", response_model=IrrigationCurrent)
def get_current_irrigation() -> dict[str, object]:
    return irrigation_service.get_current_status()


@router.get("/irrigation/runs", response_model=list[IrrigationRunRead])
def list_irrigation_runs(
    bed_id: int | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[IrrigationRun]:
    statement = select(IrrigationRun).order_by(desc(IrrigationRun.started_at)).limit(limit)
    if bed_id is not None:
        statement = statement.where(IrrigationRun.bed_id == bed_id)
    return list(db.scalars(statement).all())


@router.get("/beds/{bed_id}/irrigation/intervals", response_model=list[IrrigationInterval])
def irrigation_intervals(
    bed_id: int,
    range: str = Query(default="24h", pattern="^(6h|24h|today)$"),
    db: Session = Depends(get_db),
) -> list[IrrigationRun]:
    if db.get(Bed, bed_id) is None:
        raise HTTPException(status_code=404, detail="Beet wurde nicht gefunden")
    from datetime import datetime, timedelta

    now = datetime.utcnow()
    start = datetime.combine(now.date(), datetime.min.time()) if range == "today" else now - timedelta(hours=6 if range == "6h" else 24)
    return list(
        db.scalars(
            select(IrrigationRun)
            .where(IrrigationRun.bed_id == bed_id, IrrigationRun.started_at >= start)
            .order_by(IrrigationRun.started_at)
        ).all()
    )
