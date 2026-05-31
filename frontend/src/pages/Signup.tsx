import { Link } from 'react-router-dom';
import { Building2, Stethoscope, UserRound } from 'lucide-react';
import { Card } from '../components/common';
import { cn } from '@/lib/utils';

const SIGNUP_TYPES = [
  {
    to: '/signup/patient',
    title: 'Patient',
    description: 'Book appointments with doctors',
    icon: UserRound,
  },
  {
    to: '/signup/doctor',
    title: 'Doctor (individual)',
    description: 'Manage your own practice',
    icon: Stethoscope,
  },
  {
    to: '/signup/hospital',
    title: 'Clinic / hospital',
    description: 'Manage multiple doctors and operations',
    icon: Building2,
  },
] as const;

export function Signup() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card padding="lg" className="w-full max-w-lg">
        <div className="text-center mb-6">
          <h1 className="text-xl font-bold text-text-primary">Create an account</h1>
          <p className="text-sm text-text-secondary mt-1">Choose how you will use the app</p>
        </div>
        <ul className="space-y-3">
          {SIGNUP_TYPES.map(({ to, title, description, icon: Icon }) => (
            <li key={to}>
              <Link
                to={to}
                className={cn(
                  'flex gap-4 rounded-xl border border-border/80 bg-card p-4 text-left transition-colors',
                  'hover:border-primary/40 hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary'
                )}
              >
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <Icon className="h-5 w-5" aria-hidden />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="font-semibold text-text-primary">{title}</p>
                  <p className="text-sm text-text-secondary mt-0.5">{description}</p>
                </div>
              </Link>
            </li>
          ))}
        </ul>
        <p className="mt-8 text-center text-sm text-text-muted">
          <Link to="/login" className="text-primary font-medium hover:underline">
            Back to sign in
          </Link>
        </p>
      </Card>
    </div>
  );
}
