import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AuthProvider, useAuth } from "./auth/AuthContext";
import { RequireAuth } from "./auth/RequireAuth";
import { Layout } from "./components/Layout";
import { AdminPage } from "./pages/AdminPage";
import { FloorEditorPage } from "./pages/FloorEditorPage";
import { LoginPage } from "./pages/LoginPage";
import { MyReservationsPage } from "./pages/MyReservationsPage";
import { NotificationsPage } from "./pages/NotificationsPage";
import { RegisterPage } from "./pages/RegisterPage";
import { RestaurantDetailPage } from "./pages/RestaurantDetailPage";
import { RestaurantsPage } from "./pages/RestaurantsPage";
import { StaffDashboardPage } from "./pages/StaffDashboardPage";

function Home() {
  const { user, booting } = useAuth();
  if (booting) return <div className="page muted">Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role === "admin") return <Navigate to="/admin" replace />;
  if (user.role === "waiter" || user.role === "manager") return <Navigate to="/staff" replace />;
  return <Navigate to="/restaurants" replace />;
}

export function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route element={<Layout />}>
            <Route path="/" element={<Home />} />
            <Route element={<RequireAuth />}>
              <Route path="/restaurants" element={<RestaurantsPage />} />
              <Route path="/restaurants/:id" element={<RestaurantDetailPage />} />
              <Route path="/reservations" element={<MyReservationsPage />} />
              <Route path="/notifications" element={<NotificationsPage />} />
            </Route>
            <Route element={<RequireAuth roles={["waiter", "manager", "admin"]} />}>
              <Route path="/staff" element={<StaffDashboardPage />} />
            </Route>
            <Route element={<RequireAuth roles={["manager", "admin"]} />}>
              <Route path="/editor" element={<FloorEditorPage />} />
            </Route>
            <Route element={<RequireAuth roles={["admin"]} />}>
              <Route path="/admin" element={<AdminPage />} />
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
