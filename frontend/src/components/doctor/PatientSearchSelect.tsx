import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import type { Patient } from '../../types';

export interface PatientSearchSelectProps {
  id: string;
  patients: Patient[];
  value: string;
  onChange: (patientId: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function PatientSearchSelect({
  id,
  patients,
  value,
  onChange,
  disabled,
  placeholder = 'Search patient…',
}: PatientSearchSelectProps) {
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const blurTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const selected = useMemo(() => patients.find((p) => String(p.id) === value), [patients, value]);

  useEffect(() => {
    if (selected) setQuery(selected.name || 'Patient');
    else if (!value) setQuery('');
  }, [selected, value]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return patients;
    return patients.filter((p) => (p.name || '').toLowerCase().includes(q));
  }, [patients, query]);

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, []);

  const clearBlurTimer = () => {
    if (blurTimer.current) {
      clearTimeout(blurTimer.current);
      blurTimer.current = null;
    }
  };

  const pick = useCallback(
    (p: Patient) => {
      onChange(String(p.id));
      setQuery(p.name || 'Patient');
      setOpen(false);
    },
    [onChange]
  );

  return (
    <div ref={rootRef} className="relative">
      <Input
        id={id}
        type="search"
        autoComplete="off"
        placeholder={placeholder}
        value={query}
        disabled={disabled}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
          if (value) onChange('');
        }}
        onFocus={() => {
          clearBlurTimer();
          setOpen(true);
        }}
        onBlur={() => {
          blurTimer.current = setTimeout(() => setOpen(false), 150);
        }}
        role="combobox"
        aria-expanded={open}
        aria-controls={`${id}-listbox`}
        aria-autocomplete="list"
        className="mt-1"
      />
      {open && !disabled && filtered.length > 0 && (
        <ul
          id={`${id}-listbox`}
          role="listbox"
          className={cn(
            'absolute z-50 mt-1 max-h-52 w-full overflow-auto rounded-md border border-border bg-popover text-popover-foreground shadow-md'
          )}
        >
          {filtered.map((p) => (
            <li key={String(p.id)} role="option" aria-selected={String(p.id) === value}>
              <button
                type="button"
                className="flex w-full px-3 py-2 text-left text-sm hover:bg-accent"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => pick(p)}
              >
                {p.name || 'Patient'}
              </button>
            </li>
          ))}
        </ul>
      )}
      {open && !disabled && query.trim() && filtered.length === 0 && (
        <p className="absolute z-50 mt-1 w-full rounded-md border border-border bg-popover px-3 py-2 text-sm text-muted-foreground shadow-md">
          No matches.
        </p>
      )}
    </div>
  );
}
