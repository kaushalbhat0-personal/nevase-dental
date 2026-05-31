/**
 * workspace/layouts/OperationsWorkspaceLayout.tsx
 *
 * Operations workspace layout.
 *
 * Composes:
 * - Existing AppLayout (sidebar, header)
 * - Contextual header with operational indicators
 *
 * DESIGN:
 * - Operational focus: alerts, activity, staff tasks
 * - Reduced clutter: no clinical/procurement noise
 * - Quick actions for activity feed
 */

import { Outlet } from 'react-router-dom';
import AppLayout from '../../components/layout/AppLayout';
import { ContextualHeader } from './contextual-header';
import { useAuth } from '../../hooks/useAuth';

export function OperationsWorkspaceLayout() {
  const { user, logout } = useAuth();

  return (
    <AppLayout user={user} onLogout={logout}>
      <ContextualHeader workspaceSlug="operations" />
      <Outlet />
    </AppLayout>
  );
}
