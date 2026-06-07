from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Bed
from app.schemas import BedCreate, BedRead, BedUpdate
from app.services.registry import irrigation_service, mqtt_service, relay_service, settings

router = APIRouter(prefix="/api/beds", tags=["beds"])


def _bed_or_404(db: Session, bed_id: int) -> Bed:
    bed = db.get(Bed, bed_id)
    if bed is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Beet wurde nicht gefunden")
    return bed


def _read_bed(bed: Bed) -> BedRead:
    data = BedRead.model_validate(bed)
    data.pump_running = irrigation_service.is_bed_running(bed)
    data.auto_watering_blocked_until = irrigation_service.auto_watering_blocked_until(bed)
    data.auto_watering_block_remaining_seconds = irrigation_service.auto_watering_block_remaining_seconds(bed)
    return data


def _validate_relay_pin(relay_pin: int | None) -> None:
    if relay_pin is None:
        return
    allowed_pins = set(settings.relay_pin_list)
    if relay_pin not in allowed_pins:
        allowed = ", ".join(str(pin) for pin in sorted(allowed_pins))
        raise HTTPException(status_code=422, detail=f"Relay-GPIO muss einer der verdrahteten Pins sein: {allowed}")
    if relay_pin == settings.dht21_gpio_pin:
        raise HTTPException(status_code=422, detail="Relay-GPIO darf nicht dem DHT21-Datenpin entsprechen")


@router.get("", response_model=list[BedRead])
def list_beds(db: Session = Depends(get_db)) -> list[BedRead]:
    return [_read_bed(bed) for bed in db.query(Bed).order_by(Bed.id).all()]


@router.post("", response_model=BedRead, status_code=status.HTTP_201_CREATED)
def create_bed(payload: BedCreate, db: Session = Depends(get_db)) -> BedRead:
    _validate_relay_pin(payload.relay_pin)
    bed = Bed(**payload.model_dump())
    db.add(bed)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Relay-Pin oder ADS-Kanal ist bereits vergeben") from exc
    db.refresh(bed)
    relay_service.controller.setup([bed.relay_pin])
    relay_service.turn_off(bed)
    mqtt_service.publish_bed_state(bed)
    return _read_bed(bed)


@router.get("/{bed_id}", response_model=BedRead)
def get_bed(bed_id: int, db: Session = Depends(get_db)) -> BedRead:
    return _read_bed(_bed_or_404(db, bed_id))


@router.put("/{bed_id}", response_model=BedRead)
def update_bed(bed_id: int, payload: BedUpdate, db: Session = Depends(get_db)) -> BedRead:
    bed = _bed_or_404(db, bed_id)
    _validate_relay_pin(payload.relay_pin)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(bed, key, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Relay-Pin oder ADS-Kanal ist bereits vergeben") from exc
    db.refresh(bed)
    mqtt_service.publish_bed_state(bed)
    return _read_bed(bed)


@router.delete("/{bed_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bed(bed_id: int, db: Session = Depends(get_db)) -> None:
    bed = _bed_or_404(db, bed_id)
    if irrigation_service.is_bed_running(bed):
        raise HTTPException(status_code=409, detail="Beet wird gerade bewässert")
    relay_service.turn_off(bed)
    db.delete(bed)
    db.commit()
