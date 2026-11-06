from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from geoalchemy2.shape import from_shape
from shapely.geometry import Polygon
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.db.models import (
    CustomerRecord,
    DeliveryAgentRecord,
    OptimizationRunRecord,
    OrderRecord,
    ZoneRecord,
)
from app.schemas import (
    Customer,
    CustomerCreate,
    DailyRequirementUpdate,
    DeliveryAgent,
    DeliveryAgentCreate,
    Order,
    OrderCreate,
    OrderStatusUpdate,
    Route,
    RouteStop,
    TrafficUpdate,
    TrafficUpdateResult,
    Zone,
    ZoneCreate,
)
from app.services.matrix import HaversineMatrixProvider
from app.services.optimizer import StopInput, optimize_single_agent_route
from app.services.zone_assignment import assign_zone

router = APIRouter()


@router.post("/zones", response_model=Zone, status_code=status.HTTP_201_CREATED)
def create_zone(payload: ZoneCreate, db: Session = Depends(get_db)) -> ZoneRecord:
    if payload.boundary[0] != payload.boundary[-1]:
        raise HTTPException(
            status_code=422, detail="Polygon boundary must be closed (first point = last point)"
        )
    polygon = Polygon(payload.boundary)
    if not polygon.is_valid or polygon.area == 0:
        raise HTTPException(status_code=422, detail="Zone boundary must be a valid polygon")

    zone = ZoneRecord(
        name=payload.name,
        boundary=from_shape(polygon, srid=4326),
    )
    db.add(zone)
    db.commit()
    db.refresh(zone)
    return zone


@router.post("/customers", response_model=Customer, status_code=status.HTTP_201_CREATED)
def create_customer(payload: CustomerCreate, db: Session = Depends(get_db)) -> CustomerRecord:
    try:
        zone = assign_zone(db, payload.latitude, payload.longitude, payload.zone_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    customer = CustomerRecord(
        name=payload.name,
        phone=payload.phone,
        latitude=payload.latitude,
        longitude=payload.longitude,
        daily_requirement_liters=payload.daily_requirement_liters,
        zone_id=zone.id,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.patch(
    "/customers/{customer_id}/daily-requirement", response_model=Customer
)
def update_daily_requirement(
    customer_id: int,
    payload: DailyRequirementUpdate,
    db: Session = Depends(get_db),
) -> CustomerRecord:
    customer = db.get(CustomerRecord, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    customer.daily_requirement_liters = payload.daily_requirement_liters
    db.commit()
    db.refresh(customer)
    return customer


@router.post("/orders", response_model=Order, status_code=status.HTTP_201_CREATED)
def create_order(payload: OrderCreate, db: Session = Depends(get_db)) -> OrderRecord:
    customer = db.get(CustomerRecord, payload.customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    order = OrderRecord(
        customer_id=payload.customer_id,
        delivery_date=payload.delivery_date,
        quantity_liters=payload.quantity_liters,
        status="active",
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


@router.patch("/orders/{order_id}/status", response_model=Order)
def update_order_status(
    order_id: int,
    payload: OrderStatusUpdate,
    db: Session = Depends(get_db),
) -> OrderRecord:
    order = db.get(OrderRecord, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    order.status = payload.status
    db.commit()
    db.refresh(order)
    return order


@router.post(
    "/delivery-agents",
    response_model=DeliveryAgent,
    status_code=status.HTTP_201_CREATED,
)
def create_delivery_agent(
    payload: DeliveryAgentCreate, db: Session = Depends(get_db)
) -> DeliveryAgentRecord:
    if db.get(ZoneRecord, payload.zone_id) is None:
        raise HTTPException(status_code=404, detail="Zone not found")
    agent = DeliveryAgentRecord(**payload.model_dump())
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


@router.put(
    "/customers/{customer_id}/traffic", response_model=TrafficUpdateResult
)
def update_customer_traffic(
    customer_id: int, payload: TrafficUpdate, db: Session = Depends(get_db)
) -> CustomerRecord:
    customer = db.get(CustomerRecord, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    customer.traffic_severity = payload.severity
    customer.traffic_updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(customer)
    return customer


@router.post("/optimization/runs", response_model=Route)
def optimize_route(
    agent_id: int,
    delivery_date: date,
    db: Session = Depends(get_db),
) -> Route:
    agent = db.get(DeliveryAgentRecord, agent_id)
    if agent is None or not agent.active:
        raise HTTPException(status_code=404, detail="Active delivery agent not found")

    rows = db.execute(
        select(
            CustomerRecord,
            func.sum(OrderRecord.quantity_liters).label("quantity_liters"),
        )
        .join(OrderRecord, OrderRecord.customer_id == CustomerRecord.id)
        .where(
            CustomerRecord.zone_id == agent.zone_id,
            CustomerRecord.daily_requirement_liters > 0,
            OrderRecord.delivery_date == delivery_date,
            OrderRecord.status == "active",
            OrderRecord.quantity_liters > 0,
        )
        .group_by(CustomerRecord.id)
        .order_by(CustomerRecord.id)
    ).all()

    # Ineligible customers and empty zones are removed before a matrix is built.
    if not rows:
        return Route(
            status="no_active_orders",
            agent_id=agent.id,
            zone_id=agent.zone_id,
            delivery_date=delivery_date,
            stops=[],
            estimated_travel_minutes=0,
            message="No active, non-vacation orders in this agent's zone.",
        )

    stop_inputs = [
        StopInput(
            customer_id=customer.id,
            name=customer.name,
            latitude=customer.latitude,
            longitude=customer.longitude,
            demand_milliliters=round(quantity_liters * 1000),
            traffic_severity=customer.traffic_severity,
        )
        for customer, quantity_liters in rows
    ]
    if sum(stop.demand_milliliters for stop in stop_inputs) > round(
        agent.capacity_liters * 1000
    ):
        raise HTTPException(
            status_code=422,
            detail="Active order quantity exceeds this agent's vehicle capacity",
        )

    coordinates = [
        (agent.depot_latitude, agent.depot_longitude),
        *((stop.latitude, stop.longitude) for stop in stop_inputs),
    ]
    matrix = HaversineMatrixProvider().build_travel_time_matrix(coordinates)
    settings = get_settings()
    try:
        result = optimize_single_agent_route(
            stops=stop_inputs,
            travel_time_matrix=matrix,
            capacity_milliliters=round(agent.capacity_liters * 1000),
            traffic_penalty_weight=settings.traffic_penalty_weight,
        )
    except (ValueError, RuntimeError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    route = Route(
        status="optimized",
        agent_id=agent.id,
        zone_id=agent.zone_id,
        delivery_date=delivery_date,
        stops=[
            RouteStop(
                sequence=stop.sequence,
                customer_id=stop.stop.customer_id,
                customer_name=stop.stop.name,
                latitude=stop.stop.latitude,
                longitude=stop.stop.longitude,
                quantity_liters=stop.stop.demand_milliliters / 1000,
                traffic_severity=stop.stop.traffic_severity,
                estimated_arrival_minutes=stop.estimated_arrival_minutes,
            )
            for stop in result.stops
        ],
        estimated_travel_minutes=result.estimated_travel_minutes,
    )
    run = OptimizationRunRecord(
        agent_id=agent.id,
        delivery_date=delivery_date,
        status=route.status,
        result=route.model_dump(mode="json"),
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    route.run_id = run.id
    return route


@router.get("/optimization/runs/{run_id}", response_model=Route)
def get_optimization_run(run_id: int, db: Session = Depends(get_db)) -> Route:
    run = db.get(OptimizationRunRecord, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Optimization run not found")
    return Route.model_validate({**run.result, "run_id": run.id})
