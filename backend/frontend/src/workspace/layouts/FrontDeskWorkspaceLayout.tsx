/**
 * workspace/layouts/FrontDeskWorkspaceLayout.tsx
 *
 * Front Desk workspace layout.
 *
 * Composes:
 * - Existing AppLayout (sidebar, header)
 * - Contextual header with operational indicators
 *
 * DESIGN:
 * - Operations focus: arrivals, queue, walk-ins
 * - Reduced clutter: no clinical/admin noise
 * - Quick actions for new appointments
 */

import { Outlet } from 'react-router-dom';
import AppLayout from '../../components/layout/AppLayout';
import { ContextualHeader } from './contextual-header';
import { useAuth } from '../../hooks/useAuth';

export function FrontDeskWorkspaceLayout() {
  const { user, logout } = useAuth();

  return (
    <AppLayout user={user} onLogout={logout}>
      <ContextualHeader workspaceSlug="frontdesk" />
      <Outlet />
    </AppLayout>
  );
}
