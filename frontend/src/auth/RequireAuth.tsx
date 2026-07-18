import { Navigate, Outlet, useLocation } from "react-router-dom";

import type { Role } from "../api/types";
import { useAuth } from "./AuthContext";

export function RequireAuth({ roles }: { roles?: Role[] }) {
  const { user, booting } = useAuth();
  const location = useLocation();

  if (booting) {
    return <div className="page muted">Loading session…</div>;
  }
  if (!user) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }
  if (roles && !roles.includes(user.role)) {
    return <Navigate to="/" replace />;
  }
  return <Outlet />;
}
