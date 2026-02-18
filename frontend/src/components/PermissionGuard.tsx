import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

interface PermissionGuardProps {
  /** Single permission string required to access this route */
  permission?: string;
  /** Multiple permissions — user needs ANY of them */
  anyOf?: string[];
  /** Fallback path if unauthorized (defaults to /) */
  redirectTo?: string;
  children: React.ReactNode;
}

/**
 * Route guard that checks permissions before rendering children.
 *
 * Usage:
 *   <Route path="/admin/users" element={
 *     <PermissionGuard permission="admin.users.view">
 *       <UserManagement />
 *     </PermissionGuard>
 *   } />
 */
export default function PermissionGuard({
  permission,
  anyOf,
  redirectTo = '/',
  children,
}: PermissionGuardProps) {
  const { can, canAny } = useAuth();

  if (permission && !can(permission)) {
    return <Navigate to={redirectTo} replace />;
  }

  if (anyOf && anyOf.length > 0 && !canAny(...anyOf)) {
    return <Navigate to={redirectTo} replace />;
  }

  return <>{children}</>;
}
