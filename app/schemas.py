from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=5, max_length=20)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    daily_requirement_liters: float = Field(default=0, ge=0)
    zone_id: int | None = None


class DailyRequirementUpdate(BaseModel):
    daily_requirement_liters: float = Field(ge=0)


class Customer(BaseModel):
    id: int
    name: str
    phone: str
    latitude: float
    longitude: float
    daily_requirement_liters: float
    traffic_severity: float
    zone_id: int

    model_config = ConfigDict(from_attributes=True)


class OrderCreate(BaseModel):
    customer_id: int
    delivery_date: date
    quantity_liters: float = Field(gt=0)


class Order(BaseModel):
    id: int
    customer_id: int
    delivery_date: date
    quantity_liters: float
    status: Literal["active", "cancelled"]

    model_config = ConfigDict(from_attributes=True)


class OrderStatusUpdate(BaseModel):
    status: Literal["active", "cancelled"]


class ZoneCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    # Each coordinate is [longitude, latitude]; the polygon must be closed.
    boundary: list[tuple[float, float]] = Field(min_length=4)


class Zone(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class DeliveryAgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    zone_id: int
    capacity_liters: float = Field(gt=0)
    depot_latitude: float = Field(ge=-90, le=90)
    depot_longitude: float = Field(ge=-180, le=180)


class DeliveryAgent(BaseModel):
    id: int
    name: str
    zone_id: int
    capacity_liters: float
    depot_latitude: float
    depot_longitude: float
    active: bool

    model_config = ConfigDict(from_attributes=True)


class TrafficUpdate(BaseModel):
    severity: float = Field(ge=0, le=1, description="0 is free-flowing; 1 is severe")


class RouteStop(BaseModel):
    sequence: int
    customer_id: int
    customer_name: str
    latitude: float
    longitude: float
    quantity_liters: float
    traffic_severity: float
    estimated_arrival_minutes: int


class Route(BaseModel):
    run_id: int | None = None
    status: Literal["optimized", "no_active_orders"]
    agent_id: int
    zone_id: int
    delivery_date: date
    stops: list[RouteStop]
    estimated_travel_minutes: int
    skipped_customer_ids: list[int] = Field(default_factory=list)
    message: str | None = None


class TrafficUpdateResult(BaseModel):
    customer_id: int
    traffic_severity: float
    traffic_updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
