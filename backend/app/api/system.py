from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import SystemEvent
from app.schemas import SystemEventRead, SystemStatus
from app.services.registry import irrigation_service, mqtt_service, system_service

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/status", response_model=SystemStatus)
def get_status(db: Session = Depends(get_db)) -> dict[str, object]:
    return system_service.get_status(
        db,
        irrigation_running=irrigation_service.is_any_irrigation_running(),
        mqtt_connected=mqtt_service.connected,
    )


@router.get("/events", response_model=list[SystemEventRead])
def list_events(limit: int = Query(default=100, ge=1, le=500), db: Session = Depends(get_db)) -> list[SystemEvent]:
    return list(db.scalars(select(SystemEvent).order_by(desc(SystemEvent.created_at)).limit(limit)).all())
