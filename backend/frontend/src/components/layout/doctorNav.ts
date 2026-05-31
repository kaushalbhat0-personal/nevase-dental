import type { LucideIcon } from 'lucide-react';
import { Calendar, Clock, Home, Users } from 'lucide-react';

/**
 * Legacy clinician nav — kept for backward compatibility with DoctorSidebar.
 * Only clinical flows: no billing, no inventory, no admin.
 * The authoritative nav source is WORKSPACE_REGISTRY in workspace/registry.tsx.
 */
export const DOCTOR_PRACTICE_NAV: { path: string; label: string; icon: LucideIcon }[] = [
  { path: '/doctor/dashboard', label: 'Queue', icon: Home },
  { path: '/doctor/patients', label: 'Patients', icon: Users },
  { path: '/doctor/appointments', label: 'Encounters', icon: Calendar },
  { path: '/doctor/availability', label: 'Availability', icon: Clock },
];
