/**
 * workspace/layouts/ProcurementWorkspaceLayout.tsx
 *
 * Procurement workspace layout.
 *
 * Composes:
 * - Existing AppLayout (sidebar, header)
 * - Contextual header with operational indicators
 *
 * DESIGN:
 * - Supply chain focus: inventory, suppliers, purchase orders
 * - Reduced clutter: no patient-care/clinical noise
 * - Quick actions for new orders
 */

import { Outlet } from 'react-router-dom';
import AppLayout from '../../components/layout/AppLayout';
import { ContextualHeader } from './contextual-header';
import { useAuth } from '../../hooks/useAuth';

export function ProcurementWorkspaceLayout() {
  const { user, logout } = useAuth();

  return (
    <AppLayout user={user} onLogout={logout}>
      <ContextualHeader workspaceSlug="procurement" />
      <Outlet />
    </AppLayout>
  );
}
