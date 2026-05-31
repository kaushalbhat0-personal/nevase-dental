/**
 * workspace/layouts/PatientWorkspaceLayout.tsx
 *
 * Patient workspace layout.
 *
 * Composes:
 * - Existing PatientLayout (mobile-first, bottom nav)
 * - Contextual header with operational indicators
 *
 * DESIGN:
 * - Patient focus: home, care, messages, discover
 * - Mobile-first with bottom navigation
 * - Reduced clutter: no staff/admin noise
 *
 * NOTE: This is a route-level layout that wraps PatientLayout.
 * PatientLayout already provides <Outlet /> internally.
 */

import { PatientLayout } from '../../components/layout/PatientLayout';
import { ContextualHeader } from './contextual-header';

/**
 * PatientWorkspaceLayout wraps PatientLayout and adds a contextual header.
 * PatientLayout already renders <Outlet /> for nested routes.
 */
export function PatientWorkspaceLayout() {
  return (
    <>
      <ContextualHeader workspaceSlug="patient" />
      <PatientLayout />
    </>
  );
}
