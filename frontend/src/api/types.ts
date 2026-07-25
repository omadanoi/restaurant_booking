export type Role = "customer" | "waiter" | "manager" | "admin";

export interface User {
  id: string;
  email: string;
  full_name: string;
  phone: string | null;
  role: Role;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface Restaurant {
  id: string;
  name: string;
  description: string | null;
  address: string;
  city: string;
  country: string;
  timezone: string;
  phone: string | null;
  email: string | null;
  cuisine_type: string | null;
  is_active: boolean;
  deposit_enabled: boolean;
  /** Decimal serialized as a string by the API — display only, no arithmetic. */
  deposit_amount: string | null;
  deposit_currency: string;
  cancellation_cutoff_hours: number;
  latitude: number | null;
  longitude: number | null;
}

export interface Floor {
  id: string;
  restaurant_id: string;
  name: string;
  level: number;
  width: number;
  height: number;
  background_image_url: string | null;
}

export type TableShape = "rectangle" | "circle" | "square";
export type TableStatus = "available" | "occupied" | "reserved" | "cleaning" | "out_of_service";

export interface DiningTable {
  id: string;
  restaurant_id: string;
  floor_id: string;
  table_number: string;
  x: number;
  y: number;
  rotation: number;
  shape: TableShape;
  capacity: number;
  min_capacity: number | null;
  status: TableStatus;
  is_indoor: boolean;
  is_accessible: boolean;
  is_active: boolean;
}

export type ElementType =
  | "wall"
  | "door"
  | "window"
  | "restroom"
  | "bar"
  | "entrance"
  | "kitchen"
  | "plant"
  | "label";

export interface FloorElement {
  id: string;
  restaurant_id: string;
  floor_id: string;
  element_type: ElementType;
  x: number;
  y: number;
  width: number;
  height: number;
  rotation: number;
  label: string | null;
}

export type ReservationStatus =
  | "pending"
  | "confirmed"
  | "seated"
  | "completed"
  | "cancelled"
  | "no_show";

export type DepositStatus = "none" | "pending" | "paid" | "refunded" | "forfeited";

export interface Reservation {
  id: string;
  restaurant_id: string;
  table_id: string;
  customer_id: string;
  start_time: string;
  end_time: string;
  party_size: number;
  status: ReservationStatus;
  source: string;
  special_requests: string | null;
  deposit_amount: string | null;
  deposit_currency: string | null;
  deposit_status: DepositStatus;
  created_at: string;
}

export interface OpeningHours {
  day_of_week: number;
  opens_at: string | null;
  closes_at: string | null;
  is_closed: boolean;
}

export interface AppNotification {
  id: string;
  type: string;
  channel: string;
  status: string;
  payload: Record<string, unknown>;
  reservation_id: string | null;
  restaurant_id: string | null;
  sent_at: string | null;
  created_at: string;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface RealtimeEvent {
  type: string;
  data: Record<string, unknown>;
}
