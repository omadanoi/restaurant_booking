from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    floor_elements,
    floors,
    health,
    notifications,
    reservations,
    restaurants,
    tables,
    users,
    ws,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(restaurants.router)
api_router.include_router(floors.router)
api_router.include_router(floor_elements.router)
api_router.include_router(tables.router)
api_router.include_router(reservations.router)
api_router.include_router(notifications.router)
api_router.include_router(ws.router)
