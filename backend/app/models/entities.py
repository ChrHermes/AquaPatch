from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Bed(Base):
    __tablename__ = "beds"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    relay_pin: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    ads_channel: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    moisture_dry_raw: Mapped[int] = mapped_column(Integer, default=26000, nullable=False)
    moisture_wet_raw: Mapped[int] = mapped_column(Integer, default=12000, nullable=False)
    watering_seconds: Mapped[int] = mapped_column(Integer, default=120, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    readings: Mapped[list["MoistureReading"]] = relationship(back_populates="bed", cascade="all, delete-orphan")
    irrigation_runs: Mapped[list["IrrigationRun"]] = relationship(back_populates="bed", cascade="all, delete-orphan")


class MoistureReading(Base):
    __tablename__ = "moisture_readings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    bed_id: Mapped[int] = mapped_column(ForeignKey("beds.id", ondelete="CASCADE"), index=True)
    raw_value: Mapped[int] = mapped_column(Integer, nullable=False)
    voltage: Mapped[float] = mapped_column(Float, nullable=False)
    moisture_percent: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    bed: Mapped[Bed] = relationship(back_populates="readings")


class IrrigationRun(Base):
    __tablename__ = "irrigation_runs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    bed_id: Mapped[int] = mapped_column(ForeignKey("beds.id", ondelete="CASCADE"), index=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    trigger: Mapped[str] = mapped_column(String(40), default="manual", nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    message: Mapped[str] = mapped_column(Text, default="", nullable=False)

    bed: Mapped[Bed] = relationship(back_populates="irrigation_runs")


class SystemEvent(Base):
    __tablename__ = "system_events"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    level: Mapped[str] = mapped_column(String(20), nullable=False)
    component: Mapped[str] = mapped_column(String(80), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
