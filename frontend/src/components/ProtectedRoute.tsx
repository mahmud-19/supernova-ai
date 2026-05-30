import { Navigate, Outlet } from 'react-router-dom';
import { Role, useAuth } from '../auth/AuthContext';

export function ProtectedRoute({ roles }: { roles?: Role[] }) {
  const { user, loading } = useAuth();
  if (loading) {
    return <main className="centered">Loading session...</main>;
  }
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  if (roles && !roles.includes(user.role)) {
    if (user.role === 'admin') {
      return <Navigate to="/admin/dashboard" replace />;
    }
    return <Navigate to={user.role === 'sonologist' ? '/upload' : '/review'} replace />;
  }
  return <Outlet />;
}
