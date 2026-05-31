import { cn } from '@/lib/utils';
import { DISPLAY_TIMEZONE } from '../../constants/time';
import {
  formatSlotTimeWithZoneLabel,
  isSlotInstantInThePast,
  slotKey,
} from '../../utils/doctorSchedule';
import { groupDoctorSlotsByDayPart } from '../../utils/slotTimeGroups';
import type { DoctorSlot } from '../../services/doctors';

type DoctorSlotPickerProps = {
  slots: DoctorSlot[];
  bookDate: string;
  doctorTodayYmd: string;
  selectedSlotStart: string | null;
  onSelect: (key: string) => void;
  disabled?: boolean;
  /** next available slot for subtle highlight */
  nextAvailableKey: string | null;
};

export function DoctorSlotPicker({
  slots,
  bookDate,
  doctorTodayYmd,
  selectedSlotStart,
  onSelect,
  disabled,
  nextAvailableKey,
}: DoctorSlotPickerProps) {
  const groups = groupDoctorSlotsByDayPart(slots, DISPLAY_TIMEZONE);

  return (
    <div className="space-y-5" role="listbox" aria-label="Available times by part of day">
      {groups.map(({ part, label, slots: gSlots }) => (
        <div key={part} className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{label}</p>
          <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3">
            {gSlots.map((slot) => {
              const pastOnToday = bookDate === doctorTodayYmd && isSlotInstantInThePast(slot.start);
              const sk = slotKey(slot.start);
              const selected = selectedSlotStart != null && slotKey(selectedSlotStart) === sk;
              const isDisabled = !slot.available || pastOnToday || disabled;
              const booked = !slot.available;
              const isNext = nextAvailableKey != null && sk === nextAvailableKey;

              return (
                <button
                  key={sk}
                  type="button"
                  data-testid="slot-button"
                  disabled={isDisabled}
                  aria-pressed={selected}
                  aria-label={
                    isNext
                      ? `${formatSlotTimeWithZoneLabel(slot.start, DISPLAY_TIMEZONE)} — next available`
                      : formatSlotTimeWithZoneLabel(slot.start, DISPLAY_TIMEZONE)
                  }
                  onClick={() => onSelect(sk)}
                  className={cn(
                    'flex min-h-[48px] w-full items-center justify-center rounded-xl border-2 px-2 text-center text-sm font-semibold tabular-nums transition-all duration-200',
                    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                    pastOnToday && 'border-border/60 bg-muted/50 text-muted-foreground cursor-not-allowed',
                    !pastOnToday &&
                      booked &&
                      'border-destructive/20 bg-destructive/5 text-destructive cursor-not-allowed',
                    !pastOnToday &&
                      !booked &&
                      selected &&
                      'border-primary bg-primary text-primary-foreground shadow-md scale-[1.02]',
                    !pastOnToday &&
                      !booked &&
                      !selected &&
                      'border-border bg-white text-foreground shadow-sm hover:border-primary/30 hover:shadow',
                    isNext && !selected && !pastOnToday && !booked && 'ring-2 ring-[#22c55e]/50 border-[#22c55e]/40'
                  )}
                >
                  <span className="flex flex-col items-center leading-tight">
                    <span>{formatSlotTimeWithZoneLabel(slot.start, DISPLAY_TIMEZONE)}</span>
                    {isNext && !booked && !selected && !pastOnToday && (
                      <span className="text-[10px] font-medium text-[#16a34a]">Next</span>
                    )}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
