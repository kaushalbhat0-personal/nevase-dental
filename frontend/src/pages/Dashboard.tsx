import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { Users, Stethoscope, Calendar, DollarSign } from 'lucide-react';
import { useAuth, useDashboard } from '../hooks';
import { getEffectiveRoles, isPatientRole } from '../utils/roles';
import { ErrorState, EmptyState, Button } from '../components/common';
import { SkeletonCard } from '../components/common/skeletons';
import { FadeContent, staggerContainer, staggerItem } from '../animations';
import { Card, CardContent } from '@/components/ui/card';

export function Dashboard() {
  const navigate = useNavigate();
  const { user } = useAuth();

  // Data fetching via hook
  const { stats, loading, error, refetch } = useDashboard();
  const showStaffQuickActions = !isPatientRole(getEffectiveRoles(user, localStorage.getItem('token')));

  // Quick action navigation handlers
  const handleAddPatient = () => navigate('/patients', { state: { showForm: true } });
  const handleAddDoctor = () => navigate('/doctors', { state: { showForm: true } });
  const handleNewAppointment = () => navigate('/appointments', { state: { showForm: true } });
  const handleCreateBill = () => navigate('/billing', { state: { showForm: true } });

  // Show skeletons only during initial data fetch (when still loading and no valid data yet)
  // Prevents flicker by checking loading state first
  const showSkeletons = loading && !error;

  // Empty state: data loaded successfully but all counts are zero
  const isEmpty =
    !loading &&
    !error &&
    stats.total_patients === 0 &&
    stats.total_doctors === 0;

  return (
    <div className="page-container max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      {showSkeletons && (
        <motion.div
          initial={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
          className="space-y-6 sm:space-y-8"
        >
          <div className="space-y-2">
            <div className="h-8 bg-surface rounded-xl w-48 animate-pulse" />
            <div className="h-4 bg-surface rounded-lg w-64 animate-pulse" />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </div>
        </motion.div>
      )}

      {error && (
        <ErrorState
          title="Failed to load dashboard"
          description="Unable to fetch dashboard statistics. Please try again."
          error={error}
          onRetry={refetch}
        />
      )}

      {!error && !loading && isEmpty && (
        <EmptyState
          title="No data available"
          description="Dashboard statistics are currently empty. Add patients, doctors, or appointments to see data here."
        />
      )}

      {!error && !showSkeletons && (
        <FadeContent show={!showSkeletons}>
          <div className="space-y-6">
            {/* Header */}
            <div className="flex justify-between items-center">
              <div>
                <h1 className="text-2xl font-semibold">Dashboard</h1>
                <p className="text-sm text-muted-foreground mt-1">Overview of your hospital's performance</p>
              </div>
            </div>

            {/* Stats Grid */}
            <motion.div
              className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6"
              variants={staggerContainer}
              initial="initial"
              animate="animate"
            >
              <motion.div variants={staggerItem}>
                <Card>
                  <CardContent className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                      <Users className="w-5 h-5 text-primary" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-muted-foreground">Total Patients</p>
                      <p className="text-2xl font-bold">{(stats?.total_patients ?? 0).toLocaleString()}</p>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>

              <motion.div variants={staggerItem}>
                <Card>
                  <CardContent className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                      <Stethoscope className="w-5 h-5 text-primary" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-muted-foreground">Total Doctors</p>
                      <p className="text-2xl font-bold">{(stats?.total_doctors ?? 0).toLocaleString()}</p>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>

              <motion.div variants={staggerItem}>
                <Card>
                  <CardContent className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                      <Calendar className="w-5 h-5 text-primary" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-muted-foreground">Today's Appointments</p>
                      <p className="text-2xl font-bold">{stats?.today_appointments ?? 0}</p>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>

              <motion.div variants={staggerItem}>
                <Card>
                  <CardContent className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                      <DollarSign className="w-5 h-5 text-primary" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-muted-foreground">Total Revenue</p>
                      <p className="text-2xl font-bold">${(stats?.total_revenue ?? 0).toLocaleString()}</p>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            </motion.div>

            {/* Quick Actions */}
            {showStaffQuickActions && (
              <motion.div
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.25, delay: 0.3, ease: [0.4, 0, 0.2, 1] }}
              >
                <h2 className="text-lg font-semibold mb-4">Quick Actions</h2>
                <div className="flex flex-wrap gap-3">
                  <Button variant="secondary" onClick={handleAddPatient}>
                    Add Patient
                  </Button>
                  <Button variant="secondary" onClick={handleAddDoctor}>
                    Add Doctor
                  </Button>
                  <Button variant="secondary" onClick={handleNewAppointment}>
                    New Appointment
                  </Button>
                  <Button variant="secondary" onClick={handleCreateBill}>
                    Create Bill
                  </Button>
                </div>
              </motion.div>
            )}
          </div>
        </FadeContent>
      )}
    </div>
  );
}
