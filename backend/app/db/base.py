"""Import every model module so Base.metadata is fully populated before
Alembic (or anything else) inspects it. Nothing else should import this
module except Alembic's env.py and tooling that needs the full metadata.
"""

from app.db.base_class import Base  # noqa: F401
from app.models import (  # noqa: F401
    AuditLog,
    EmployeeRestaurant,
    Floor,
    FloorElement,
    Holiday,
    Notification,
    OpeningHours,
    RefreshToken,
    Reservation,
    Restaurant,
    Table,
    TableStatusLog,
    User,
)
