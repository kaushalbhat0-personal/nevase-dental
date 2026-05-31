/**
 * workspace/layouts/DoctorWorkspaceLayout.tsx
 *
 * Doctor workspace layout.
 *
 * Composes:
 * - Existing DoctorLayoutInner logic (sidebar, header, verification strips)
 * - Contextual header with operational indicators
 *
 * DESIGN:
 * - Clinical focus: queue, encounters, patients
 * - Reduced clutter: no admin/procurement/finance noise
 * - Verification-aware: shows status indicators
 *
 * NOTE: This is a route-level layout that wraps DoctorLayout.
 * DoctorLayout already provides <Outlet /> internally.
 */

import { DoctorLayout } from '../../components/layout/DoctorLayout';
import { ContextualHeader } from './contextual-header';

/**
 * DoctorWorkspaceLayout wraps DoctorLayout and adds a contextual header.
 * DoctorLayout already renders <Outlet /> for nested routes.
 */
export function DoctorWorkspaceLayout() {
  return (
    <>
      <ContextualHeader workspaceSlug="doctor" />
      <DoctorLayout />
    </>
  );
}
