# Subscription Delivery Management Backend Service

A FastAPI-based backend service for managing daily milk subscriptions, customer deliveries, geographical delivery zones, and optimized delivery routes.

The system uses **PostgreSQL with PostGIS** for geographical zone assignment and **Google OR-Tools** for single-agent vehicle route optimization.

## Key Features

- **Customer Management:** Register customers and manage their daily milk requirements.
- **Subscription & Order Management:** Create and track daily milk delivery orders.
- **Geographical Zone Assignment:** Automatically assign customers to delivery zones using PostGIS.
- **Automatic Zone Creation:** Create provisional circular zones for customers outside existing delivery zones.
- **Delivery Agent Management:** Assign delivery agents to specific zones.
- **Route Optimization:** Optimize delivery routes using Google OR-Tools.
- **Vehicle Capacity Constraints:** Ensure delivery quantities do not exceed vehicle capacity.
- **Traffic-Aware Routing:** Apply soft visit-order penalties based on traffic severity.
- **REST API:** Built with FastAPI and documented using Swagger UI.

## Tech Stack

- Python 3.11+
- FastAPI
- PostgreSQL
- PostGIS
- Google OR-Tools
- SQLAlchemy
- Haversine Distance Calculation
- Uvicorn
