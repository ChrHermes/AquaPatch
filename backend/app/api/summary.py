from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Bed, ClimateReading, IrrigationRun, MoistureReading
from app.schemas import BedDailySummary, DailySummary

router = APIRouter(prefix="/api/summary", tags=["summary"])


def _day_bounds(day: date) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min)
    return start, start + timedelta(days=1)


@router.get("/today", response_model=DailySummary)
def today_summary(db: Session = Depends(get_db)) -> DailySummary:
    return build_summary(date.today(), db)


@router.get("/daily", response_model=DailySummary)
def daily_summary(day: date = Query(alias="date"), db: Session = Depends(get_db)) -> DailySummary:
    return build_summary(day, db)


def build_summary(day: date, db: Session) -> DailySummary:
    start, end = _day_bounds(day)
    beds = db.scalars(select(Bed).order_by(Bed.id)).all()
    bed_summaries: list[BedDailySummary] = []
    total_runs = 0
    total_duration = 0

    for bed in beds:
        runs = list(
            db.scalars(
                select(IrrigationRun)
                .where(and_(IrrigationRun.bed_id == bed.id, IrrigationRun.started_at >= start, IrrigationRun.started_at < end))
                .order_by(IrrigationRun.started_at)
            ).all()
        )
        readings = list(
            db.scalars(
                select(MoistureReading).where(
                    and_(MoistureReading.bed_id == bed.id, MoistureReading.created_at >= start, MoistureReading.created_at < end)
                )
            ).all()
        )
        valid_percentages = [reading.moisture_percent for reading in readings if reading.is_valid and reading.moisture_percent is not None]
        run_duration = sum(run.duration_seconds for run in runs)
        total_runs += len(runs)
        total_duration += run_duration
        bed_summaries.append(
            BedDailySummary(
                bed_id=bed.id,
                bed_name=bed.name,
                irrigation_count=len(runs),
                total_duration_seconds=run_duration,
                last_irrigation_at=runs[-1].started_at if runs else None,
                moisture_min=round(min(valid_percentages), 1) if valid_percentages else None,
                moisture_max=round(max(valid_percentages), 1) if valid_percentages else None,
                moisture_avg=round(sum(valid_percentages) / len(valid_percentages), 1) if valid_percentages else None,
                sensor_warning_count=sum(1 for reading in readings if not reading.is_valid),
            )
        )

    climate_stats = db.execute(
        select(
            func.avg(ClimateReading.temperature_c),
            func.avg(ClimateReading.humidity_percent),
            func.min(ClimateReading.temperature_c),
            func.max(ClimateReading.temperature_c),
            func.min(ClimateReading.humidity_percent),
            func.max(ClimateReading.humidity_percent),
        ).where(and_(ClimateReading.created_at >= start, ClimateReading.created_at < end, ClimateReading.is_valid.is_(True)))
    ).one()

    return DailySummary(
        date=day.isoformat(),
        irrigation_count=total_runs,
        total_duration_seconds=total_duration,
        beds=bed_summaries,
        climate_avg_temperature_c=round(climate_stats[0], 1) if climate_stats[0] is not None else None,
        climate_avg_humidity_percent=round(climate_stats[1], 1) if climate_stats[1] is not None else None,
        climate_min_temperature_c=round(climate_stats[2], 1) if climate_stats[2] is not None else None,
        climate_max_temperature_c=round(climate_stats[3], 1) if climate_stats[3] is not None else None,
        climate_min_humidity_percent=round(climate_stats[4], 1) if climate_stats[4] is not None else None,
        climate_max_humidity_percent=round(climate_stats[5], 1) if climate_stats[5] is not None else None,
    )
