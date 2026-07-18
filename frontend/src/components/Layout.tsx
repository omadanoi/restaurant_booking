import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";

const LINKS: Record<string, { to: string; label: string }[]> = {
  customer: [
    { to: "/restaurants", label: "Restaurants" },
    { to: "/reservations", label: "My reservations" },
    { to: "/notifications", label: "Notifications" },
  ],
  waiter: [
    { to: "/staff", label: "Staff dashboard" },
    { to: "/notifications", label: "Notifications" },
  ],
  manager: [
    { to: "/staff", label: "Staff dashboard" },
    { to: "/editor", label: "Floor editor" },
    { to: "/notifications", label: "Notifications" },
  ],
  admin: [
    { to: "/admin", label: "Admin" },
    { to: "/restaurants", label: "Restaurants" },
    { to: "/staff", label: "Staff dashboard" },
    { to: "/editor", label: "Floor editor" },
  ],
};

export function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate("/login");
  }

  return (
    <>
      <nav className="nav">
        <NavLink to="/" className="brand">
          Table<span>Hub</span>
        </NavLink>
        {user &&
          LINKS[user.role].map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
            >
              {link.label}
            </NavLink>
          ))}
        <div className="spacer" />
        {user && (
          <>
            <span className="who">
              {user.full_name} · {user.role}
            </span>
            <button className="small" onClick={handleLogout}>
              Sign out
            </button>
          </>
        )}
      </nav>
      <main className="page">
        <Outlet />
      </main>
    </>
  );
}
