import { Navigate, Outlet, useLocation } from "react-router-dom";
import type { Role } from "../api/types";
import { useAuth } from "./AuthContext";

export function ProtectedRoute({ roles }: { roles?: Role[] }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <div className="page-loading" role="status">Cargando tu biblioteca…</div>;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (roles && !roles.includes(user.rol)) return <Navigate to="/" replace />;
  return <Outlet />;
}
