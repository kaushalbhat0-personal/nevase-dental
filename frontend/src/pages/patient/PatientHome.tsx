import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Calendar,
  FileText,
  Receipt,
  Clock,
  Phone,
  MessageSquare,
  MapPin,
  Loader2,
  ChevronRight,
  Download,
} from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';
import { appointmentsApi, billingApi, documentsApi } from '../../services';
import { formatAppointmentDoctorName } from '../../utils';
import type { Appointment, Bill } from '../../types';

export function PatientHome() {
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

  const completedAppts = appointments
    .filter((a) => a.status === 'completed')
    .sort((a, b) => new Date(b.scheduled_at || b.appointment_time || '').getTime() - new Date(a.scheduled_at || a.appointment_time || '').getTime())
    .slice(0, 3);

  const pendingBills = bills.filter((b) => b.status === 'unpaid').slice(0, 3);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-[#0EA5E9]" />
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-8">
      {/* Welcome header */}
      <div className="bg-gradient-to-br from-[#0EA5E9] to-[#0284C7] rounded-2xl p-6 sm:p-8 text-white -mx-4 sm:mx-0">
        <h1 className="text-xl sm:text-2xl font-bold">
          Welcome, {user?.full_name?.split(' ')[0] || 'Patient'}!
        </h1>
        <p className="text-white/70 mt-1 text-sm">Your dental health matters</p>
      </div>

      {/* Upcoming Appointment */}
      {upcomingAppt ? (
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
          <div className="flex items-center gap-2 mb-3">
            <Calendar className="w-5 h-5 text-[#0EA5E9]" />
            <h2 className="font-semibold text-[#0F172A]">Next Appointment</h2>
          </div>
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-[#0F172A]">{formatAppointmentDoctorName(upcomingAppt) || 'Doctor'}</p>
              <p className="text-sm text-[#1E293B]/60 mt-1 flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5" />
                {upcomingAppt.scheduled_at
                  ? new Date(upcomingAppt.scheduled_at).toLocaleDateString('en-IN', {
                      day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit',
                    })
                  : 'Date TBD'}
              </p>
            </div>
            <span className="bg-[#0EA5E9]/10 text-[#0EA5E9] text-xs font-medium px-3 py-1 rounded-full capitalize">
              {upcomingAppt.status}
            </span>
          </div>
          <Link
            to="/patient/appointments"
            className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-[#0EA5E9] hover:text-[#0284C7]"
          >
            View all appointments <ChevronRight className="w-4 h-4" />
          </Link>
        </div>
      ) : (
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 text-center">
          <div className="w-14 h-14 rounded-full bg-[#0EA5E9]/10 flex items-center justify-center mx-auto mb-3">
            <Calendar className="w-7 h-7 text-[#0EA5E9]" />
          </div>
          <h2 className="font-semibold text-[#0F172A]">No upcoming appointments</h2>
          <p className="text-sm text-[#1E293B]/60 mt-1 mb-4">Book your next dental visit today</p>
          <Link
            to="/patient/discover"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium text-white bg-[#0EA5E9] hover:bg-[#0284C7] transition-colors"
          >
            Book Appointment
          </Link>
        </div>
      )}

      {/* Quick Actions */}
      <div className="grid grid-cols-2 gap-3">
        <Link
          to="/patient/discover"
          className="flex flex-col items-center justify-center gap-2 bg-white rounded-2xl p-5 shadow-sm border border-gray-100 hover:shadow-md transition-all min-h-[100px]"
        >
          <div className="w-10 h-10 rounded-xl bg-[#0EA5E9]/10 flex items-center justify-center">
            <Calendar className="w-5 h-5 text-[#0EA5E9]" />
          </div>
          <span className="text-sm font-medium text-[#0F172A]">Book Appointment</span>
        </Link>
        <Link
          to="/patient/appointments"
          className="flex flex-col items-center justify-center gap-2 bg-white rounded-2xl p-5 shadow-sm border border-gray-100 hover:shadow-md transition-all min-h-[100px]"
        >
          <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center">
            <Calendar className="w-5 h-5 text-blue-600" />
          </div>
          <span className="text-sm font-medium text-[#0F172A]">My Appointments</span>
        </Link>
        <Link
          to="/patient/prescriptions"
          className="flex flex-col items-center justify-center gap-2 bg-white rounded-2xl p-5 shadow-sm border border-gray-100 hover:shadow-md transition-all min-h-[100px]"
        >
          <div className="w-10 h-10 rounded-xl bg-purple-50 flex items-center justify-center">
            <FileText className="w-5 h-5 text-purple-600" />
          </div>
          <span className="text-sm font-medium text-[#0F172A]">Prescriptions</span>
        </Link>
        <Link
          to="/patient/bills"
          className="flex flex-col items-center justify-center gap-2 bg-white rounded-2xl p-5 shadow-sm border border-gray-100 hover:shadow-md transition-all min-h-[100px]"
        >
          <div className="w-10 h-10 rounded-xl bg-green-50 flex items-center justify-center">
            <Receipt className="w-5 h-5 text-green-600" />
          </div>
          <span className="text-sm font-medium text-[#0F172A]">Bills</span>
        </Link>
      </div>

      {/* Recent Prescriptions */}
      {completedAppts.length > 0 && (
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold text-[#0F172A]">Recent Prescriptions</h2>
            <Link to="/patient/prescriptions" className="text-sm font-medium text-[#0EA5E9] hover:text-[#0284C7]">
              View all
            </Link>
          </div>
          <div className="space-y-3">
            {completedAppts.slice(0, 3).map((a) => (
              <div key={a.id} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                <div className="flex items-center gap-3">
                  <FileText className="w-4 h-4 text-[#1E293B]/40 shrink-0" />
                  <div>
                    <p className="text-sm font-medium text-[#0F172A]">{formatAppointmentDoctorName(a) || 'Doctor'}</p>
                    <p className="text-xs text-[#1E293B]/50">
                      {a.scheduled_at ? new Date(a.scheduled_at).toLocaleDateString('en-IN') : 'Date TBD'}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => documentsApi.triggerPrescriptionDownload(a.id)}
                  className="p-2 rounded-lg text-[#1E293B]/40 hover:text-purple-600 hover:bg-purple-50 transition-colors"
                  title="Download Prescription"
                >
                  <Download className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Pending Bills */}
      {pendingBills.length > 0 && (
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold text-[#0F172A]">Pending Bills</h2>
            <Link to="/patient/bills" className="text-sm font-medium text-[#0EA5E9] hover:text-[#0284C7]">
              View all
            </Link>
          </div>
          <div className="space-y-3">
            {pendingBills.map((b) => (
              <div key={b.id} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                <div className="flex items-center gap-3">
                  <Receipt className="w-4 h-4 text-[#1E293B]/40 shrink-0" />
                  <div>
                    <p className="text-sm font-medium text-[#0F172A]">
                      {b.description || 'Dental Service'}
                    </p>
                    <p className="text-xs text-[#1E293B]/50">
                      {b.created_at ? new Date(b.created_at).toLocaleDateString('en-IN') : ''}
                    </p>
                  </div>
                </div>
                <span className="text-sm font-semibold text-red-500">
                    ₹{b.amount.toLocaleString('en-IN')}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Clinic Contact Card */}
      <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
        <h2 className="font-semibold text-[#0F172A] mb-3">Contact Us</h2>
        <div className="space-y-3">
          <a
            href="tel:+918805606018"
            className="flex items-center gap-3 p-3 rounded-xl bg-gray-50 hover:bg-gray-100 transition-colors"
          >
            <div className="w-9 h-9 rounded-full bg-[#0EA5E9]/10 flex items-center justify-center">
              <Phone className="w-4 h-4 text-[#0EA5E9]" />
            </div>
            <div>
              <p className="text-sm font-medium text-[#0F172A]">Call Us</p>
              <p className="text-xs text-[#1E293B]/60">+91 8805606018</p>
            </div>
            <ChevronRight className="w-4 h-4 ml-auto text-[#1E293B]/30" />
          </a>
          <a
            href="https://wa.me/918805606018?text=Hi%2C%20I%20would%20like%20to%20book%20an%20appointment"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-3 p-3 rounded-xl bg-green-50 hover:bg-green-100 transition-colors"
          >
            <div className="w-9 h-9 rounded-full bg-green-100 flex items-center justify-center">
              <MessageSquare className="w-4 h-4 text-green-600" />
            </div>
            <div>
              <p className="text-sm font-medium text-[#0F172A]">WhatsApp</p>
              <p className="text-xs text-[#1E293B]/60">Chat with us</p>
            </div>
            <ChevronRight className="w-4 h-4 ml-auto text-[#1E293B]/30" />
          </a>
          <div className="flex items-center gap-3 p-3 rounded-xl bg-gray-50">
            <div className="w-9 h-9 rounded-full bg-gray-100 flex items-center justify-center">
              <MapPin className="w-4 h-4 text-gray-500" />
            </div>
            <div>
              <p className="text-sm font-medium text-[#0F172A]">Visit Us</p>
              <p className="text-xs text-[#1E293B]/60">Nevase Dental Clinic, Your City</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
