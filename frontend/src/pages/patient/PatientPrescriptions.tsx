import { useEffect, useState } from 'react';
import { FileText, Download, Loader2 } from 'lucide-react';
import { appointmentsApi, documentsApi } from '../../services';
import { formatAppointmentDoctorName } from '../../utils';
import type { Appointment } from '../../types';

export default function PatientPrescriptions() {
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const apps = await appointmentsApi.getAll({ limit: 100 });
        if (!cancelled) {
          setAppointments(Array.isArray(apps) ? apps : []);
        }
      } catch {
        /* silently handle */
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const completedAppts = appointments.filter((a) => a.status === 'completed');

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-[#0EA5E9]" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[#0F172A]">Prescriptions</h1>
        <p className="text-sm text-[#1E293B]/60 mt-1">View and download your prescriptions</p>
      </div>

      {completedAppts.length === 0 ? (
        <div className="bg-white rounded-2xl p-10 text-center shadow-sm border border-gray-100">
          <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <FileText className="w-8 h-8 text-gray-400" />
          </div>
          <h3 className="font-semibold text-[#0F172A]">No prescriptions yet</h3>
          <p className="text-sm text-[#1E293B]/60 mt-1">Prescriptions from completed visits will appear here</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {completedAppts.map((a) => (
            <div key={a.id} className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 hover:shadow-md transition-all">
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-4">
                  <div className="w-10 h-10 rounded-xl bg-purple-50 flex items-center justify-center shrink-0">
                    <FileText className="w-5 h-5 text-purple-600" />
                  </div>
                  <div>
                    <p className="font-semibold text-[#0F172A]">{formatAppointmentDoctorName(a) || 'Doctor'}</p>
                    <p className="text-sm text-[#1E293B]/60 mt-0.5">
                      {a.scheduled_at
                        ? new Date(a.scheduled_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' })
                        : 'Date TBD'}
                    </p>
                    {a.notes && <p className="text-sm text-[#1E293B]/50 mt-2">{a.notes}</p>}
                  </div>
                </div>
                <button
                  onClick={() => documentsApi.triggerPrescriptionDownload(a.id)}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-purple-600 bg-purple-50 hover:bg-purple-100 transition-colors"
                >
                  <Download className="w-4 h-4" />
                  <span className="hidden sm:inline">Download PDF</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
