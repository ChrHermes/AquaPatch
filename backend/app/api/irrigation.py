from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import IrrigationRun
from app.schemas import IrrigationRunRead, WaterRequest
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
