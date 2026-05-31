import { useFormContext } from 'react-hook-form';
import type { FormDatePickerProps } from './types';

export function FormDatePicker<TFieldValues extends Record<string, unknown>>({
  name,
  label,
  placeholder,
  min,
  max,
  disabled,
  required,
}: FormDatePickerProps<TFieldValues>) {
  const {
    register,
    formState: { errors },
  } = useFormContext<TFieldValues>();

  const error = errors[name];

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-foreground">
        {label}
        {required && <span className="text-destructive ml-1">*</span>}
      </label>
      <input
        type="date"
        {...register(name)}
        placeholder={placeholder}
        min={min}
        max={max}
        disabled={disabled}
        className={`w-full min-h-[44px] rounded-xl border bg-background px-4 py-2.5 text-foreground transition-all duration-200 [color-scheme:light] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background dark:[color-scheme:dark] ${
          error ? 'border-destructive focus-visible:ring-destructive/30' : 'border-input'
        }`}
      />
      {error && (
        <span className="text-sm text-destructive mt-1 block">{error.message as string}</span>
      )}
    </div>
  );
}
