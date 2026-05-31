import { Link } from 'react-router-dom';
import { Building2, ArrowLeft } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { buttonVariants } from '@/components/ui/button';
import { cn } from '@/lib/utils';

/**
 * Target for "Create Clinic" from the solo-doctor dashboard.
 * Outlines upgrading the practice to a multi-provider organization.
 */
export function ClinicOnboardingPage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-sky-50/50 via-background to-emerald-50/30 dark:from-sky-950/20 dark:via-background dark:to-emerald-950/20">
      <div className="mx-auto max-w-lg px-4 py-10">
        <Link
          to="/doctor/dashboard"
          className={cn(
            buttonVariants({ variant: 'ghost', size: 'sm' }),
            'mb-6 inline-flex gap-2 text-muted-foreground'
          )}
        >
          <ArrowLeft className="h-4 w-4" aria-hidden />
          Back to overview
        </Link>

        <Card className="border-border/80 shadow-sm">
          <CardHeader>
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Building2 className="h-5 w-5" aria-hidden />
            </div>
            <CardTitle className="text-xl pt-2">Set up your clinic or hospital</CardTitle>
            <CardDescription>
              You are on a path to add more providers, delegate scheduling, and run your organization
              as a team. This flow will guide tenant setup and team onboarding as your product
              team wires the backend.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              For now, use the doctors directory in your workspace to see who is in your
              organization. When multi-seat clinic creation is available, you will complete it from
              this page.
            </p>
            <Link
              to="/doctor/doctors"
              className={cn(buttonVariants({ variant: 'default' }), 'w-full sm:w-auto inline-flex')}
            >
              View doctors in your organization
            </Link>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
