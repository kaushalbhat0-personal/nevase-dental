import { useEffect, useState } from 'react';
import { Pill, CheckCircle, Loader2 } from 'lucide-react';
import { medicationScheduleApi } from '../../services';
import type { MedicationScheduleRead } from '../../services';

export default function PatientMedications() {
  const [medications, setMedications] = useState<MedicationScheduleRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [takenToday, setTakenToday] = useState<Set<string>>(new Set());

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const response = await medicationScheduleApi.listSchedules({ limit: 100 });
        const items = response?.items ?? (Array.isArray(response) ? response : []);
        if (!cancelled) {
          setMedications(items);
        }
      } catch {
        setMedications([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const handleMarkTaken = async (id: string) => {
    try {
      await medicationScheduleApi.recordAdherence(id, { action: 'taken', scheduled_time: new Date().toISOString() });
      setTakenToday((prev) => new Set(prev).add(id));
    } catch {
      /* silently handle */
    }
  };

  const activeMeds = medications.filter((m) => m.status === 'active' || !m.status);
  const adherenceRate = medications.length > 0
    ? Math.round((takenToday.size / Math.max(activeMeds.length, 1)) * 100)
    : 0;

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
        <h1 className="text-2xl font-bold text-[#0F172A]">Medications</h1>
        <p className="text-sm text-[#1E293B]/60 mt-1">Track your daily medication schedule</p>
      </div>

      {activeMeds.length > 0 && (
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-[#0F172A]">Today's Adherence</h3>
            <span className="text-sm font-medium text-[#0EA5E9]">{adherenceRate}%</span>
          </div>
          <div className="w-full bg-gray-100 rounded-full h-2.5">
            <div
              className="bg-[#0EA5E9] h-2.5 rounded-full transition-all duration-500"
              style={{ width: `${adherenceRate}%` }}
            />
          </div>
          <p className="text-xs text-[#1E293B]/50 mt-2">{takenToday.size} of {activeMeds.length} taken today</p>
        </div>
      )}

      {activeMeds.length === 0 ? (
        <div className="bg-white rounded-2xl p-10 text-center shadow-sm border border-gray-100">
          <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <Pill className="w-8 h-8 text-gray-400" />
          </div>
          <h3 className="font-semibold text-[#0F172A]">No active medications</h3>
          <p className="text-sm text-[#1E293B]/60 mt-1">Your prescribed medications will appear here</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {activeMeds.map((med) => {
            const isTaken = takenToday.has(String(med.id));
            return (
              <div key={med.id} className={`bg-white rounded-2xl p-6 shadow-sm border transition-all ${isTaken ? 'border-green-200 bg-green-50/30' : 'border-gray-100 hover:shadow-md'}`}>
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-4">
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${isTaken ? 'bg-green-100' : 'bg-blue-50'}`}>
                      <Pill className={`w-5 h-5 ${isTaken ? 'text-green-600' : 'text-[#0EA5E9]'}`} />
                    </div>
                    <div>
                      <p className="font-semibold text-[#0F172A]">{med.medicine_name || 'Medication'}</p>
                      <p className="text-sm text-[#1E293B]/60 mt-0.5">
                        {med.dosage || 'As prescribed'} · {med.frequency || 'As directed'}
                      </p>
                      <div className="flex gap-4 mt-3">
                        {['Morning', 'Afternoon', 'Night'].map((time) => (
                          <label key={time} className="flex items-center gap-1.5 text-xs text-[#1E293B]/60">
                            <input type="checkbox" className="rounded border-gray-300 text-[#0EA5E9] focus:ring-[#0EA5E9]" />
                            {time}
                          </label>
                        ))}
                      </div>
                    </div>
                  </div>
                  {isTaken ? (
                    <span className="flex items-center gap-1 text-xs font-medium text-green-600 bg-green-50 px-3 py-1.5 rounded-full">
                      <CheckCircle className="w-3.5 h-3.5" /> Taken
                    </span>
                  ) : (
                    <button
                      onClick={() => handleMarkTaken(String(med.id))}
                      className="px-4 py-2 rounded-lg text-sm font-medium text-[#0EA5E9] bg-[#0EA5E9]/10 hover:bg-[#0EA5E9]/20 transition-colors"
                    >
                      Mark Taken
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
