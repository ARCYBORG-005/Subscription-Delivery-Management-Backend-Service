from datetime import date, datetime

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ZoneRecord(Base):
    __tablename__ = "zones"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    boundary = mapped_column(Geometry("POLYGON", srid=4326), nullable=False, index=True)

    customers: Mapped[list["CustomerRecord"]] = relationship(back_populates="zone")
    agents: Mapped[list["DeliveryAgentRecord"]] = relationship(back_populates="zone")


class CustomerRecord(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    daily_requirement_liters: Mapped[float] = mapped_column(Float, default=0)
    traffic_severity: Mapped[float] = mapped_column(Float, default=0)
    traffic_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    zone_id: Mapped[int] = mapped_column(ForeignKey("zones.id"), index=True)

    zone: Mapped[ZoneRecord] = relationship(back_populates="customers")
    orders: Mapped[list["OrderRecord"]] = relationship(back_populates="customer")


class OrderRecord(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    delivery_date: Mapped[date] = mapped_column(Date, index=True)
    quantity_liters: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)

    customer: Mapped[CustomerRecord] = relationship(back_populates="orders")


class DeliveryAgentRecord(Base):
    __tablename__ = "delivery_agents"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    zone_id: Mapped[int] = mapped_column(ForeignKey("zones.id"), index=True)
    capacity_liters: Mapped[float] = mapped_column(Float)
    depot_latitude: Mapped[float] = mapped_column(Float)
    depot_longitude: Mapped[float] = mapped_column(Float)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    zone: Mapped[ZoneRecord] = relationship(back_populates="agents")


class OptimizationRunRecord(Base):
    __tablename__ = "optimization_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("delivery_agents.id"))
    delivery_date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(30))
    result: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
