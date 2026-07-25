import enum


class UserRole(str, enum.Enum):
    CUSTOMER = "customer"
    WAITER = "waiter"
    MANAGER = "manager"
    ADMIN = "admin"


class TableShape(str, enum.Enum):
    RECTANGLE = "rectangle"
    CIRCLE = "circle"
    SQUARE = "square"


class ElementType(str, enum.Enum):
    """Non-bookable layout features drawn on the floor plan so customers can
    read the room (a window seat, a table near the restrooms, the bar…).
    """

    WALL = "wall"
    DOOR = "door"
    WINDOW = "window"
    RESTROOM = "restroom"
    BAR = "bar"
    ENTRANCE = "entrance"
    KITCHEN = "kitchen"
    PLANT = "plant"
    LABEL = "label"


class TableStatus(str, enum.Enum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    RESERVED = "reserved"
    CLEANING = "cleaning"
    OUT_OF_SERVICE = "out_of_service"


class ReservationStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SEATED = "seated"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class ReservationSource(str, enum.Enum):
    ONLINE = "online"
    PHONE = "phone"
    WALK_IN = "walk_in"


class DepositStatus(str, enum.Enum):
    """Lifecycle of a booking deposit.

    NONE means the restaurant didn't require one. PENDING is reserved for a
    future real payment provider whose confirmation is asynchronous — the
    demo provider settles instantly, so it never produces this state.
    """

    NONE = "none"
    PENDING = "pending"
    PAID = "paid"
    REFUNDED = "refunded"
    FORFEITED = "forfeited"


class PaymentKind(str, enum.Enum):
    CHARGE = "charge"
    REFUND = "refund"


class PaymentStatus(str, enum.Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class NotificationType(str, enum.Enum):
    RESERVATION_CONFIRMED = "reservation_confirmed"
    RESERVATION_REMINDER = "reservation_reminder"
    RESERVATION_CANCELLED = "reservation_cancelled"
    TABLE_READY = "table_ready"
    WAITLIST_UPDATE = "waitlist_update"


class NotificationChannel(str, enum.Enum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"


class NotificationStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class EmployeeRoleAtRestaurant(str, enum.Enum):
    WAITER = "waiter"
    MANAGER = "manager"
