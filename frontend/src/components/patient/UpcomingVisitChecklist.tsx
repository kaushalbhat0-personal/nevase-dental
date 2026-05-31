/**
 * UpcomingVisitChecklist.tsx — Dynamic preparation checklist linked to next appointment.
 *
 * Shows doctor name, clinic, date, and tailored preparation items.
 * Still uses GENERIC reminders — no medical recommendations.
 */

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Calendar, Clock, MapPin, Stethoscope, ClipboardList } from 'lucide-react';
import dayjs from 'dayjs';
import {
  genericPreparationItems,
  preparationFooterMessage,
} from '@/utils/preparationChecklist';

interface UpcomingAppointment {
  id: string;
  appointment_time: string;
  doctor_name: string;
  doctor_specialization: string | null;
  clinic_name: string | null;
}

interface UpcomingVisitChecklistProps {
  appointment: UpcomingAppointment | null;
}

export function UpcomingVisitChecklist({ appointment }: UpcomingVisitChecklistProps) {
  const [checkedItems, setCheckedItems] = useState<Set<string>>(new Set());

  const toggleItem = (itemId: string) => {
    setCheckedItems((prev) => {
      const next = new Set(prev);
      if (next.has(itemId)) {
        next.delete(itemId);
      } else {
        next.add(itemId);
      }
      return next;
    });
  };

  if (!appointment) {
    return (
      <Card className="border border-gray-200">
        <CardContent className="p-6 text-center">
          <ClipboardList className="mx-auto h-8 w-8 text-gray-300" />
          <p className="mt-2 text-sm text-gray-500">
            No upcoming appointments. When you book one, preparation reminders will appear here.
          </p>
        </CardContent>
      </Card>
    );
  }

  const appointmentDate = dayjs(appointment.appointment_time);
  const isToday = appointmentDate.isSame(dayjs(), 'day');
  const isTomorrow = appointmentDate.isSame(dayjs().add(1, 'day'), 'day');

  return (
    <Card className="border border-gray-200">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <ClipboardList className="h-5 w-5 text-blue-500" />
          <CardTitle className="text-lg">Getting Ready for Your Visit</CardTitle>
        </div>

        {/* Appointment info */}
        <div className="mt-2 space-y-1.5 rounded-lg bg-blue-50 p-3">
          <div className="flex items-center gap-2">
            <Stethoscope className="h-4 w-4 text-blue-500" />
            <span className="font-medium text-gray-900">
              {appointment.doctor_name}
            </span>
            {appointment.doctor_specialization && (
              <Badge variant="secondary" className="text-xs">
                {appointment.doctor_specialization}
              </Badge>
            )}
          </div>

          <div className="flex items-center gap-2 text-sm text-gray-600">
            <Calendar className="h-3.5 w-3.5" />
            <span>
              {isToday
                ? 'Today'
                : isTomorrow
                  ? 'Tomorrow'
                  : appointmentDate.format('dddd, MMMM D, YYYY')}
            </span>
            <Clock className="h-3.5 w-3.5 ml-1" />
            <span>{appointmentDate.format('h:mm A')}</span>
          </div>

          {appointment.clinic_name && (
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <MapPin className="h-3.5 w-3.5" />
              <span>{appointment.clinic_name}</span>
            </div>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        <p className="text-sm text-gray-500">
          Here are some things to consider before your visit:
        </p>

        <div className="space-y-2">
          {genericPreparationItems.map((item) => (
            <div key={item.id} className="flex items-start gap-2">
              <Checkbox
                id={`visit-${item.id}`}
                checked={checkedItems.has(item.id)}
                onCheckedChange={() => toggleItem(item.id)}
                className="mt-0.5"
              />
              <div className="flex-1">
                <Label
                  htmlFor={`visit-${item.id}`}
                  className={`text-sm cursor-pointer ${
                    checkedItems.has(item.id)
                      ? 'text-gray-400 line-through'
                      : 'text-gray-700'
                  }`}
                >
                  {item.label}
                </Label>
                {item.description && (
                  <p
                    className={`text-xs mt-0.5 ${
                      checkedItems.has(item.id)
                        ? 'text-gray-300'
                        : 'text-gray-500'
                    }`}
                  >
                    {item.description}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>

        <p className="text-xs text-gray-400 italic pt-2 border-t border-gray-100">
          {preparationFooterMessage}
        </p>
      </CardContent>
    </Card>
  );
}
