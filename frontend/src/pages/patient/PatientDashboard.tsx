import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Calendar, Receipt, FileText, ArrowRight, Clock, Stethoscope } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';
import { appointmentsApi, billingApi } from '../../services';
import { formatAppointmentDoctorName } from '../../utils';
import type { Appointment, Bill } from '../../types';

export default function PatientDashboard() {
  const { user } = useAuth();
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [bills, setBills] = useState<Bill[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [apps, billsData] = await Promise.all([
          appointmentsApi.getAll({ limit: 50 }),
          billingApi.getAll({ limit: 50 }),
        ]);
        if (!cancelled) {
          setAppointments(Array.isArray(apps) ? apps : []);
          setBills(Array.isArray(billsData) ? billsData : []);
        }
      } catch {
        /* silently handle */
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const upcomingAppt = appointments
    .filter((a) => a.status === 'scheduled' || a.status === 'pending')
    .sort((a, b) => new Date(a.scheduled_at || a.appointment_time || '').getTime() - new Date(b.scheduled_at || b.appointment_time || '').getTime())
    .slice(0, 1)[0];

  const recentAppts = appointments
    .filter((a) => a.status === 'completed')
    .sort((a, b) => new Date(b.scheduled_at || b.appointment_time || '').getTime() - new Date(a.scheduled_at || a.appointment_time || '').getTime())
    .slice(0, 3);

  const pendingBills = bills.filter((b) => b.status === 'unpaid');

  if (loading) {
    return (
      <div className="space-y-6">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-32 rounded-2xl bg-gray-100 animate-pulse" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Welcome + Stats */}
      <div className="bg-gradient-to-br from-[#0EA5E9] to-[#0284C7] rounded-2xl p-6 sm:p-8 text-white">
        <h2 className="text-xl sm:text-2xl font-bold">Welcome, {user?.full_name?.split(' ')[0] || 'Patient'}!</h2>
        <p className="text-white/70 mt-1 text-sm">Manage your dental health journey</p>
        <div className="grid grid-cols-3 gap-4 mt-6">
          <div className="bg-white/15 rounded-xl p-4 backdrop-blur-sm text-center">
            <p className="text-2xl font-bold">{appointments.length}</p>
            <p className="text-xs text-white/70 mt-0.5">Appointments</p>
          </div>
          <div className="bg-white/15 rounded-xl p-4 backdrop-blur-sm text-center">
            <p className="text-2xl font-bold">{pendingBills.length}</p>
            <p className="text-xs text-white/70 mt-0.5">Pending Bills</p>
          </div>
          <div className="bg-white/15 rounded-xl p-4 backdrop-blur-sm text-center">
            <p className="text-2xl font-bold">{bills.length}</p>
            <p className="text-xs text-white/70 mt-0.5">Total Bills</p>
          </div>
        </div>
      </div>

      {/* Upcoming Appointment */}
      {upcomingAppt && (
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <div className="flex items-center gap-2 mb-4">
            <Calendar className="w-5 h-5 text-[#0EA5E9]" />
            <h3 className="font-semibold text-[#0F172A]">Next Appointment</h3>
          </div>
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-[#0F172A]">{formatAppointmentDoctorName(upcomingAppt) || 'Doctor'}</p>
              <p className="text-sm text-[#1E293B]/60 mt-1 flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5" />
                {upcomingAppt.scheduled_at
                  ? new Date(upcomingAppt.scheduled_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' })
                  : 'Date TBD'}
              </p>
            </div>
            <span className="bg-[#0EA5E9]/10 text-[#0EA5E9] text-xs font-medium px-3 py-1 rounded-full capitalize">
              {upcomingAppt.status}
            </span>
          </div>
        </div>
      )}

      {/* Recent Appointments */}
      {recentAppts.length > 0 && (
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <h3 className="font-semibold text-[#0F172A] mb-4">Recent Visits</h3>
          <div className="space-y-3">
            {recentAppts.map((a) => (
              <div key={a.id} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                <div className="flex items-center gap-3">
                  <Stethoscope className="w-4 h-4 text-[#1E293B]/40" />
                  <div>
                    <p className="text-sm font-medium text-[#0F172A]">{formatAppointmentDoctorName(a) || 'Doctor'}</p>
                    <p className="text-xs text-[#1E293B]/50">
                      {a.scheduled_at ? new Date(a.scheduled_at).toLocaleDateString('en-IN') : 'Date TBD'}
                    </p>
                  </div>
                </div>
                <span className="text-xs text-green-600 bg-green-50 px-2 py-0.5 rounded-full capitalize">{a.status}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="grid sm:grid-cols-3 gap-4">
        <Link to="/book" className="flex items-center justify-between bg-white rounded-2xl p-5 shadow-sm border border-gray-100 hover:shadow-md transition-all group">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#0EA5E9]/10 flex items-center justify-center">
              <Calendar className="w-5 h-5 text-[#0EA5E9]" />
            </div>
            <span className="font-medium text-[#0F172A] text-sm">Book Appointment</span>
          </div>
          <ArrowRight className="w-4 h-4 text-[#1E293B]/30 group-hover:text-[#0EA5E9] transition-colors" />
        </Link>
        <Link to="/patient/bills" className="flex items-center justify-between bg-white rounded-2xl p-5 shadow-sm border border-gray-100 hover:shadow-md transition-all group">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-green-50 flex items-center justify-center">
              <Receipt className="w-5 h-5 text-green-600" />
            </div>
            <span className="font-medium text-[#0F172A] text-sm">View Bills</span>
          </div>
          <ArrowRight className="w-4 h-4 text-[#1E293B]/30 group-hover:text-green-600 transition-colors" />
        </Link>
        <Link to="/patient/prescriptions" className="flex items-center justify-between bg-white rounded-2xl p-5 shadow-sm border border-gray-100 hover:shadow-md transition-all group">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-purple-50 flex items-center justify-center">
              <FileText className="w-5 h-5 text-purple-600" />
            </div>
            <span className="font-medium text-[#0F172A] text-sm">Download Prescription</span>
          </div>
          <ArrowRight className="w-4 h-4 text-[#1E293B]/30 group-hover:text-purple-600 transition-colors" />
        </Link>
      </div>
    </div>
  );
}
