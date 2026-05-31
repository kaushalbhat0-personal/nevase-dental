/**
 * workspace/layouts/FinanceWorkspaceLayout.tsx
 *
 * Finance workspace layout.
 *
 * Composes:
 * - Existing AppLayout (sidebar, header)
 * - Contextual header with operational indicators
 *
 * DESIGN:
 * - Financial focus: billing, reports, revenue
 * - Reduced clutter: no clinical/procurement noise
 * - Quick actions for new bills
 */

import { Outlet } from 'react-router-dom';
import AppLayout from '../../components/layout/AppLayout';
import { ContextualHeader } from './contextual-header';
import { useAuth } from '../../hooks/useAuth';

export function FinanceWorkspaceLayout() {
  const { user, logout } = useAuth();

  return (
    <AppLayout user={user} onLogout={logout}>
      <ContextualHeader workspaceSlug="finance" />
      <Outlet />
    </AppLayout>
  );
}
