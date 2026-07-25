import { api } from "./client";
import type {
  AppNotification,
  DiningTable,
  ElementType,
  Floor,
  FloorElement,
  OpeningHours,
  Paginated,
  Reservation,
  Restaurant,
  TableStatus,
  TokenPair,
  User,
} from "./types";

// -- auth ---------------------------------------------------------------------

export const login = (email: string, password: string) =>
  api<TokenPair>("/auth/login", { method: "POST", form: { username: email, password } });

export const register = (data: {
  email: string;
  password: string;
  full_name: string;
  phone?: string;
}) => api<User>("/auth/register", { method: "POST", body: data });

export const logout = (refresh_token: string) =>
  api<void>("/auth/logout", { method: "POST", body: { refresh_token } });

export const fetchMe = () => api<User>("/users/me");

// -- restaurants --------------------------------------------------------------

export const listRestaurants = (query: { city?: string; limit?: number; offset?: number } = {}) =>
  api<Paginated<Restaurant>>("/restaurants", { query });

export const getRestaurant = (id: string) => api<Restaurant>(`/restaurants/${id}`);

export const updateRestaurant = (
  id: string,
  data: Partial<
    Pick<
      Restaurant,
      | "name"
      | "description"
      | "phone"
      | "cuisine_type"
      | "deposit_enabled"
      | "deposit_amount"
      | "deposit_currency"
      | "latitude"
      | "longitude"
    >
  >,
) => api<Restaurant>(`/restaurants/${id}`, { method: "PATCH", body: data });

export const createRestaurant = (data: Partial<Restaurant>) =>
  api<Restaurant>("/restaurants", { method: "POST", body: data });

export const suspendRestaurant = (id: string) =>
  api<Restaurant>(`/restaurants/${id}`, { method: "DELETE" });

export const getOpeningHours = (restaurantId: string) =>
  api<OpeningHours[]>(`/restaurants/${restaurantId}/opening-hours`);

export const setOpeningHours = (restaurantId: string, items: OpeningHours[]) =>
  api<OpeningHours[]>(`/restaurants/${restaurantId}/opening-hours`, {
    method: "PUT",
    body: { items },
  });

// -- floors & tables ----------------------------------------------------------

export const listFloors = (restaurantId: string) =>
  api<Floor[]>(`/restaurants/${restaurantId}/floors`);

export const createFloor = (restaurantId: string, data: { name: string; level?: number }) =>
  api<Floor>(`/restaurants/${restaurantId}/floors`, { method: "POST", body: data });

export const listTables = (restaurantId: string, floorId?: string) =>
  api<DiningTable[]>(`/restaurants/${restaurantId}/tables`, {
    query: { floor_id: floorId },
  });

export const createTable = (
  restaurantId: string,
  data: { floor_id: string; table_number: string; capacity: number } & Partial<DiningTable>,
) => api<DiningTable>(`/restaurants/${restaurantId}/tables`, { method: "POST", body: data });

export const updateTable = (
  restaurantId: string,
  tableId: string,
  data: Partial<DiningTable>,
) => api<DiningTable>(`/restaurants/${restaurantId}/tables/${tableId}`, { method: "PATCH", body: data });

export const deactivateTable = (restaurantId: string, tableId: string) =>
  api<DiningTable>(`/restaurants/${restaurantId}/tables/${tableId}`, { method: "DELETE" });

export const changeTableStatus = (
  restaurantId: string,
  tableId: string,
  status: TableStatus,
  note?: string,
) =>
  api<DiningTable>(`/restaurants/${restaurantId}/tables/${tableId}/status`, {
    method: "POST",
    body: { status, note },
  });

// -- floor elements (walls, doors, windows, restrooms…) -----------------------

export const listElements = (restaurantId: string, floorId?: string) =>
  api<FloorElement[]>(`/restaurants/${restaurantId}/elements`, {
    query: { floor_id: floorId },
  });

export const createElement = (
  restaurantId: string,
  data: { floor_id: string; element_type: ElementType } & Partial<FloorElement>,
) => api<FloorElement>(`/restaurants/${restaurantId}/elements`, { method: "POST", body: data });

export const updateElement = (
  restaurantId: string,
  elementId: string,
  data: Partial<FloorElement>,
) =>
  api<FloorElement>(`/restaurants/${restaurantId}/elements/${elementId}`, {
    method: "PATCH",
    body: data,
  });

export const deleteElement = (restaurantId: string, elementId: string) =>
  api<void>(`/restaurants/${restaurantId}/elements/${elementId}`, { method: "DELETE" });

// -- reservations -------------------------------------------------------------

export const findAvailability = (
  restaurantId: string,
  query: {
    start_time: string;
    end_time: string;
    party_size: number;
    indoor?: boolean;
    accessible?: boolean;
  },
) => api<DiningTable[]>(`/restaurants/${restaurantId}/availability`, { query });

export const createReservation = (data: {
  table_id: string;
  start_time: string;
  end_time: string;
  party_size: number;
  special_requests?: string;
  payment?: { card_number?: string };
}) => api<Reservation>("/reservations", { method: "POST", body: data });

export const myReservations = (query: { limit?: number; offset?: number } = {}) =>
  api<Paginated<Reservation>>("/reservations/me", { query });

export const cancelReservation = (id: string) =>
  api<Reservation>(`/reservations/${id}/cancel`, { method: "POST" });

export const restaurantReservations = (
  restaurantId: string,
  query: { on_date?: string; status?: string; limit?: number } = {},
) => api<Paginated<Reservation>>(`/restaurants/${restaurantId}/reservations`, { query });

export const changeReservationStatus = (id: string, status: string) =>
  api<Reservation>(`/reservations/${id}/status`, { method: "POST", body: { status } });

// -- notifications & admin ----------------------------------------------------

export const myNotifications = (query: { limit?: number; offset?: number } = {}) =>
  api<Paginated<AppNotification>>("/notifications/me", { query });

export const listUsers = (query: { limit?: number; offset?: number } = {}) =>
  api<Paginated<User>>("/users", { query });
