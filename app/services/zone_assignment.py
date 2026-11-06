from uuid import uuid4

from geoalchemy2 import Geography
from sqlalchemy import cast, func, select, text
from sqlalchemy.orm import Session
from uuid import uuid4

from app.core.config import get_settings
from app.db.models import ZoneRecord


def assign_zone(
    db: Session, latitude: float, longitude: float, requested_zone_id: int | None
) -> ZoneRecord:
    if requested_zone_id is not None:
        zone = db.get(ZoneRecord, requested_zone_id)
        if zone is None:
            raise ValueError(f"Zone {requested_zone_id} does not exist")
        return zone

    point = func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)
    containing_zone = db.scalar(
        select(ZoneRecord)
        .where(func.ST_Contains(ZoneRecord.boundary, point))
        .limit(1)
    )
    if containing_zone is not None:
        return containing_zone

    point_geography = cast(point, Geography(srid=4326))
    zone_geography = cast(ZoneRecord.boundary, Geography(srid=4326))
    nearest = db.execute(
        select(
            ZoneRecord,
            func.ST_Distance(zone_geography, point_geography).label("distance_meters"),
        ).order_by("distance_meters")
    ).first()

    settings = get_settings()
    if nearest is not None and nearest.distance_meters <= settings.auto_assign_radius_km * 1000:
        return nearest.ZoneRecord

    # No existing service zone is close enough: create a small provisional zone
    # around the new customer so that it can receive a route and be optimized.
    name = f"Auto zone {latitude:.5f},{longitude:.5f} {uuid4().hex[:8]}"
    zone_id = db.execute(
        text(
            """
            INSERT INTO zones (name, boundary)
            VALUES (
                :name,
                ST_Buffer(
                    ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)::geography,
                    :radius_meters
                )::geometry
            )
            RETURNING id
            """
        ),
        {
            "name": name,
            "longitude": longitude,
            "latitude": latitude,
            "radius_meters": settings.new_zone_radius_meters,
        },
    ).scalar_one()
    zone = db.get(ZoneRecord, zone_id)
    if zone is None:
        raise RuntimeError("New zone could not be loaded after creation")
    return zone
