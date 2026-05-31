/**
 * workspace/layouts/index.ts
 *
 * Barrel exports for workspace layouts.
 */

export { ContextualHeader } from './contextual-header';
export type { WorkspaceStatusIndicator, WorkspaceQuickAction, WorkspaceContextConfig } from './contextual-header';
export { getWorkspaceContext } from './contextual-header';

export { DoctorWorkspaceLayout } from './DoctorWorkspaceLayout';
export { FrontDeskWorkspaceLayout } from './FrontDeskWorkspaceLayout';
export { OperationsWorkspaceLayout } from './OperationsWorkspaceLayout';
export { ProcurementWorkspaceLayout } from './ProcurementWorkspaceLayout';
export { FinanceWorkspaceLayout } from './FinanceWorkspaceLayout';
export { PatientWorkspaceLayout } from './PatientWorkspaceLayout';
