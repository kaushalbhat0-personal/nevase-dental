import { useEffect, useState } from 'react';
import { Eye, FileText, Download, Loader2, Pill, X } from 'lucide-react';
import { appointmentsApi, documentsApi, encountersApi } from '../../services';
import { formatAppointmentDoctorName } from '../../utils';
import type { Appointment, EncounterDetailAggregate } from '../../types';

export default function PatientPrescriptions() {
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(true);
  const [viewingEncounter, setViewingEncounter] = useState<EncounterDetailAggregate | null>(null);

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

  const handleViewPrescription = async (appointmentId: string) => {
    try {
      const encounter = await encountersApi.getById(appointmentId);
      setViewingEncounter(encounter);
    } catch {
      /* silently handle */
    }
  };

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
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleViewPrescription(a.id)}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-[#0EA5E9] bg-[#0EA5E9]/10 hover:bg-[#0EA5E9]/20 transition-colors"
                  >
                    <Eye className="w-4 h-4" />
                    <span className="hidden sm:inline">View Prescription</span>
                  </button>
                  <button
                    onClick={() => documentsApi.triggerPrescriptionDownload(a.id)}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-purple-600 bg-purple-50 hover:bg-purple-100 transition-colors"
                  >
                    <Download className="w-4 h-4" />
                    <span className="hidden sm:inline">Download PDF</span>
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Prescription Detail Modal */}
      {viewingEncounter && (
        <div
          className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/40"
          onClick={() => setViewingEncounter(null)}
        >
          <div
            className="bg-white rounded-t-2xl sm:rounded-2xl shadow-xl w-full sm:max-w-lg max-h-[85vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="sticky top-0 bg-white z-10 flex items-center justify-between px-5 py-4 border-b border-gray-100">
              <h2 className="text-lg font-bold text-[#0F172A]">Prescription Details</h2>
              <button
                onClick={() => setViewingEncounter(null)}
                className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <X className="w-5 h-5 text-[#1E293B]/60" />
              </button>
            </div>

            {/* Doctor & Date */}
            <div className="px-5 py-4 bg-gray-50/50">
              <p className="font-semibold text-[#0F172A]">
                {formatAppointmentDoctorName(viewingEncounter.appointment) || 'Doctor'}
              </p>
              <p className="text-sm text-[#1E293B]/60 mt-0.5">
                {viewingEncounter.appointment.scheduled_at
                  ? new Date(viewingEncounter.appointment.scheduled_at).toLocaleDateString('en-IN', {
                      day: 'numeric',
                      month: 'long',
                      year: 'numeric',
                    })
                  : 'Date TBD'}
              </p>
            </div>

            {/* Prescriptions */}
            <div className="px-5 py-4 space-y-4">
              {(!viewingEncounter.prescriptions || viewingEncounter.prescriptions.length === 0) ? (
                <p className="text-sm text-[#1E293B]/60 italic text-center py-8">
                  No prescription data available for this visit.
                </p>
              ) : (
                viewingEncounter.prescriptions.map((rx) => (
                  <div key={rx.id} className="rounded-xl border border-gray-100 p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <Pill className="w-4 h-4 text-[#0EA5E9]" />
                      <span className="text-xs font-medium text-[#1E293B]/60 uppercase tracking-wide">
                        Prescription
                      </span>
                      <span className="text-xs text-[#1E293B]/40 ml-auto">
                        {new Date(rx.created_at).toLocaleDateString()}
                      </span>
                    </div>
                    {rx.notes && (
                      <p className="text-sm text-[#1E293B]/70 mb-3 pb-3 border-b border-gray-100">
                        {rx.notes}
                      </p>
                    )}
                    <div className="space-y-2">
                      {rx.items.map((item, idx) => (
                        <div
                          key={idx}
                          className="rounded-lg border border-gray-100 bg-gray-50/50 p-3"
                        >
                          <p className="font-semibold text-[#0F172A] text-sm">
                            {item.medicine_name}
                          </p>
                          <div className="mt-1.5 text-xs text-[#1E293B]/70 space-y-0.5">
                            {item.dosage && <p>Dosage: {item.dosage}</p>}
                            {item.frequency && <p>Frequency: {item.frequency}</p>}
                            {item.duration && <p>Duration: {item.duration}</p>}
                            {item.instructions && (
                              <p className="italic text-[#1E293B]/50">
                                {item.instructions}
                              </p>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
