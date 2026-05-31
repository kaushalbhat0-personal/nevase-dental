import { useFetch } from './useFetch';
import {
  fetchAppointmentDataHandler,
  fetchDoctorAppointmentsViewHandler,
} from '../../handlers';
import { safeArray } from '../../utils';
import type { Appointment, Patient, Doctor } from '../../types';
import type { DoctorAppointmentsListTab } from '../../handlers/appointmentHandler';

export interface AppointmentFilters {
  doctor_id?: string;
  status?: 'scheduled' | 'completed' | 'cancelled';
  type?: 'past' | 'upcoming';
}

export function useAppointments(filters?: AppointmentFilters, enabled: boolean = true) {
  const { data, loading, refetching, error, refetch } = useFetch(
    fetchAppointmentDataHandler,
    filters,
    'appointments',
    enabled,
    { subscribeScopeEvents: enabled }
  );

  return {
    appointments: safeArray<Appointment>(data?.appointments),
    patients: safeArray<Patient>(data?.patients),
    doctors: safeArray<Doctor>(data?.doctors),
    loading,
    refetching,
    error,
    refetch,
  };
}

export function useDoctorAppointmentsView(listTab: DoctorAppointmentsListTab) {
  const { data, loading, refetching, error, refetch } = useFetch(
    fetchDoctorAppointmentsViewHandler,
    listTab,
    'doctorAppointmentsView'
  );

  return {
    listAppointments: safeArray<Appointment>(data?.appointments),
    calendarAppointments: safeArray<Appointment>(data?.calendarAppointments),
    patients: safeArray<Patient>(data?.patients),
    doctors: safeArray<Doctor>(data?.doctors),
    loading,
    refetching,
    error,
    refetch,
  };
}
