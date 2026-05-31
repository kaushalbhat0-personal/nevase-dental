/**
 * workspace/registry.tsx
 *
 * Workspace Registry — the single source of truth for all workspace definitions.
 *
 * Each workspace defines:
 * - label & icon for the sidebar header
 * - sidebar sections with nav items
 * - landing route (default page)
 * - quick actions (contextual shortcuts)
 *
 * This replaces scattered hardcoded nav arrays (staffNavBase, adminModeNavBase,
 * patientFallbackNavItems, DOCTOR_PRACTICE_NAV) with a single declarative registry.
 *
 * DESIGN PRINCIPLES:
 * - Calm, focused, uncluttered navigation
 * - Each workspace sees ONLY its own operational context
 * - No cross-role clutter
 * - Preserves existing routes — does NOT redesign routing
 */

import type { LucideIcon } from 'lucide-react';
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Bell,
  Building2,
  Calendar,
  CalendarCheck,
  CalendarPlus,
  ClipboardList,
  Clock,
  CreditCard,
  FileText,
  HeartPulse,
  Home,
  Hospital,
  LayoutDashboard,
  MessageSquare,
  Package,
  Palette,
  Pill,
  Receipt,
  Search,
  ShoppingCart,
  Stethoscope,
  Syringe,
  Truck,
  User,
  UserPlus,
  UserRound,
  Users,
  Wallet,
} from 'lucide-react';

/* ──────────────────────────────────────────────
 * Types
 * ────────────────────────────────────────────── */

export type WorkspaceSlug =
  | 'frontdesk'
  | 'doctor'
  | 'nurse'
  | 'operations'
  | 'procurement'
  | 'finance'
  | 'admin'
  | 'patient';

export interface WorkspaceNavItem {
  path: string;
  label: string;
  icon: LucideIcon;
}

export interface WorkspaceSidebarSection {
  /** Optional section header label (e.g. "Clinical", "Operations") */
  title?: string;
  items: WorkspaceNavItem[];
}

export interface WorkspaceConfig {
  /** Unique slug */
  id: WorkspaceSlug;
  /** Human-readable label for sidebar header */
  label: string;
  /** Icon for sidebar header */
  icon: LucideIcon;
  /** Short description of this workspace */
  description: string;
  /** Default landing route */
  landingRoute: string;
  /** Sidebar navigation sections */
  sections: WorkspaceSidebarSection[];
  /** Contextual quick actions (shown in sidebar footer or header) */
  quickActions?: WorkspaceNavItem[];
}

/* ──────────────────────────────────────────────
 * Workspace Registry
 * ────────────────────────────────────────────── */

export const WORKSPACE_REGISTRY: Record<WorkspaceSlug, WorkspaceConfig> = {
  /* ── FRONTDESK ─────────────────────────────── */
  frontdesk: {
    id: 'frontdesk',
    label: 'Front Desk',
    icon: ClipboardList,
    description: 'Patient arrivals, queue, and scheduling',
    landingRoute: '/appointments',
    sections: [
      {
        title: 'Operations',
        items: [
          { path: '/appointments', label: 'Arrivals', icon: CalendarCheck },
          { path: '/queue', label: 'Queue', icon: Clock },
          { path: '/appointments', label: 'Walk-ins', icon: UserRound },
          { path: '/appointments', label: 'Scheduling', icon: Calendar },
        ],
      },
    ],
    quickActions: [
      { path: '/appointments', label: 'New Appointment', icon: CalendarPlus },
    ],
  },

  /* ── DOCTOR ────────────────────────────────── */
  doctor: {
    id: 'doctor',
    label: 'Clinician',
    icon: Stethoscope,
    description: 'Schedule, patients, and clinical care',
    landingRoute: '/doctor/dashboard',
    sections: [
      {
        title: 'Clinical',
        items: [
          { path: '/doctor/dashboard', label: 'Queue', icon: Clock },
          { path: '/doctor/appointments', label: 'Encounters', icon: Stethoscope },
          { path: '/doctor/appointments', label: 'Prescriptions', icon: Pill },
          { path: '/doctor/appointments', label: 'Follow-ups', icon: CalendarCheck },
        ],
      },
      {
        title: 'Practice',
        items: [
          { path: '/doctor/patients', label: 'Patients', icon: Users },
          { path: '/doctor/availability', label: 'Availability', icon: Calendar },
        ],
      },
    ],
    quickActions: [
      { path: '/doctor/appointments', label: 'New Encounter', icon: Stethoscope },
    ],
  },

  /* ── NURSE ─────────────────────────────────── */
  nurse: {
    id: 'nurse',
    label: 'Nurse',
    icon: Syringe,
    description: 'Vitals, queue, and clinical tasks',
    landingRoute: '/queue',
    sections: [
      {
        title: 'Clinical',
        items: [
          { path: '/queue', label: 'Queue', icon: Clock },
          { path: '/appointments', label: 'Vitals', icon: Activity },
          { path: '/appointments', label: 'Tasks', icon: ClipboardList },
        ],
      },
    ],
  },

  /* ── OPERATIONS ────────────────────────────── */
  operations: {
    id: 'operations',
    label: 'Operations',
    icon: Activity,
    description: 'Clinic operations, staff, and activity',
    landingRoute: '/dashboard',
    sections: [
      {
        title: 'Overview',
        items: [
          { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
          { path: '/dashboard', label: 'Activity', icon: Activity },
          { path: '/dashboard', label: 'Staff Tasks', icon: Users },
          { path: '/dashboard', label: 'Clinic Overview', icon: Hospital },
        ],
      },
    ],
  },

  /* ── PROCUREMENT ───────────────────────────── */
  procurement: {
    id: 'procurement',
    label: 'Procurement',
    icon: ShoppingCart,
    description: 'Inventory, suppliers, and purchase orders',
    landingRoute: '/admin/inventory',
    sections: [
      {
        title: 'Supply Chain',
        items: [
          { path: '/admin/inventory', label: 'Inventory', icon: Package },
          { path: '/admin/procurement', label: 'Suppliers', icon: Truck },
          { path: '/admin/procurement', label: 'Purchase Orders', icon: FileText },
          { path: '/admin/inventory', label: 'Stock Alerts', icon: AlertTriangle },
        ],
      },
    ],
    quickActions: [
      { path: '/admin/procurement', label: 'New Order', icon: ShoppingCart },
    ],
  },

  /* ── FINANCE ───────────────────────────────── */
  finance: {
    id: 'finance',
    label: 'Finance',
    icon: Wallet,
    description: 'Billing, reports, and revenue',
    landingRoute: '/billing',
    sections: [
      {
        title: 'Financial',
        items: [
          { path: '/billing', label: 'Billing', icon: CreditCard },
          { path: '/admin/financial-dashboard', label: 'Tax Exports', icon: FileText },
          { path: '/billing', label: 'Revenue Reports', icon: BarChart3 },
          { path: '/billing', label: 'Dues', icon: Receipt },
        ],
      },
    ],
  },

  /* ── ADMIN ─────────────────────────────────── */
  admin: {
    id: 'admin',
    label: 'Admin',
    icon: Building2,
    description: "Nevase's Dental Clinic",
    landingRoute: '/admin/dashboard',
    sections: [
      {
        title: 'Management',
        items: [
          { path: '/admin/dashboard', label: 'Dashboard', icon: LayoutDashboard },
          { path: '/patients', label: 'Patients', icon: Users },
          { path: '/appointments', label: 'Appointments', icon: Calendar },
          { path: '/doctors', label: 'Doctors', icon: Stethoscope },
          { path: '/billing', label: 'Billing', icon: Receipt },
          { path: '/admin/inventory', label: 'Inventory', icon: Package },
        ],
      },
      {
        title: 'Settings',
        items: [
          { path: '/admin/branding', label: 'Branding', icon: Palette },
          { path: '/admin/communications', label: 'Communications', icon: Bell },
          { path: '/admin/reports', label: 'Reports', icon: BarChart3 },
        ],
      },
    ],
    quickActions: [
      { path: '/patients', label: 'Add Patient', icon: UserPlus },
      { path: '/appointments', label: 'New Appointment', icon: CalendarPlus },
    ],
  },

  /* ── PATIENT ───────────────────────────────── */
  patient: {
    id: 'patient',
    label: 'Care',
    icon: HeartPulse,
    description: 'Your health workspace',
    landingRoute: '/patient/home',
    sections: [
      {
        title: 'Your Care',
        items: [
          { path: '/patient/home', label: 'Home', icon: Home },
          { path: '/patient/care', label: 'Care', icon: HeartPulse },
          { path: '/patient/messages', label: 'Messages', icon: MessageSquare },
          { path: '/patient/discover', label: 'Discover', icon: Search },
          { path: '/patient/profile', label: 'Profile', icon: User },
        ],
      },
    ],
  },
};

/* ──────────────────────────────────────────────
 * Helpers
 * ────────────────────────────────────────────── */

/** Get a flat list of all nav items across all sections for a workspace. */
export function getWorkspaceNavItems(slug: WorkspaceSlug): WorkspaceNavItem[] {
  const ws = WORKSPACE_REGISTRY[slug];
  if (!ws) return [];
  return ws.sections.flatMap((s) => s.items);
}

/** Get all workspace slugs. */
export function getAllWorkspaceSlugs(): WorkspaceSlug[] {
  return Object.keys(WORKSPACE_REGISTRY) as WorkspaceSlug[];
}

/** Check if a workspace slug is valid. */
export function isValidWorkspace(slug: string): slug is WorkspaceSlug {
  return slug in WORKSPACE_REGISTRY;
}
