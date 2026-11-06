# Milk Delivery Optimizer

FastAPI starter backend for daily milk orders, PostGIS zone assignment, and
single-agent vehicle routing with Google OR-Tools.

## Run locally

1. Install Python 3.11 or newer.
2. Start a PostgreSQL database with PostGIS. Docker is optional:
   - With Docker: `docker compose up -d db`
   - Without Docker: install PostgreSQL and its PostGIS extension, create a
     database named `milk_delivery`, then enable PostGIS in that database with
     `CREATE EXTENSION postgis;` (for example, in pgAdmin's Query Tool).
3. Create and activate a virtual environment, then install dependencies:
   `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and set `DATABASE_URL` to match your local
   PostgreSQL username, password, and port.
5. Start the API: `uvicorn app.main:app --reload`
6. Open `http://localhost:8000/docs`.

The app creates its tables on startup for this student MVP. Use Alembic
migrations before deploying or collaborating on a production database.
This starter uses PostGIS-specific geometry and queries, so SQLite will not
work without changing the database models and zone-assignment implementation.

## Initial setup with the API

Create a zone first using `POST /api/zones`. Polygon points are
`[longitude, latitude]` pairs and the first pair must be repeated at the end.
Create a delivery agent for that zone using `POST /api/delivery-agents`, then
register customers and create their daily orders.

Customer registration automatically assigns a point inside an existing zone.
If it is outside all zone polygons but within `AUTO_ASSIGN_RADIUS_KM` of a
zone boundary, the nearest zone is used. Otherwise, a provisional circular
zone is created around the customer. That makes the customer available to an
agent assigned to the new zone; re-optimizing includes their coordinates as a
new stop and calculates the best route for that run.

## Optimization behavior

`POST /api/optimization/runs?agent_id=1&delivery_date=2026-11-06`
optimizes one active agent and their zone for the requested date.

Customers with a zero daily requirement (vacation mode), customers without an
active positive-quantity order, and zones with no eligible orders are excluded
before the distance matrix is built. Empty zones return `no_active_orders`
without calling the matrix provider or OR-Tools. Milk quantities are enforced
against the agent's vehicle capacity.

Traffic severity is a number from 0 (free-flowing) to 1 (severe), updated with
`PUT /api/customers/{customer_id}/traffic`. OR-Tools receives a soft visit-order
penalty: higher-severity stops are penalized when scheduled too early. The
weight is controlled by `TRAFFIC_PENALTY_WEIGHT`; this is a preference, not a
guarantee when other route constraints or travel costs conflict.

The included Haversine matrix provider is only a development estimate (straight
line distance, detour multiplier, and assumed average speed). Replace
`HaversineMatrixProvider` with a Google Maps or TomTom implementation for
real-world ETAs and traffic-aware travel times. The traffic endpoint currently
accepts externally sourced severity; it does not call either provider.

## API outline

- `POST /api/zones`
- `POST /api/customers`
- `PATCH /api/customers/{customer_id}/daily-requirement`
- `POST /api/orders`
- `PATCH /api/orders/{order_id}/status`
- `POST /api/delivery-agents`
- `PUT /api/customers/{customer_id}/traffic`
- `POST /api/optimization/runs`
- `GET /api/optimization/runs/{run_id}`
- `GET /health`

Run unit tests with `python -m unittest discover -s tests -v`.
