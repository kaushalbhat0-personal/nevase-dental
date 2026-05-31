import { useFormContext } from 'react-hook-form';
import type { FormSelectProps } from './types';

export function FormSelect<TFieldValues extends Record<string, unknown>>({
  name,
  label,
  options,
  placeholder,
  disabled,
  required,
}: FormSelectProps<TFieldValues>) {
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
      <select
        {...register(name)}
        disabled={disabled}
        className={`w-full min-h-[44px] rounded-xl border bg-background px-4 py-2.5 text-foreground transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background ${
          error ? 'border-destructive focus-visible:ring-destructive/30' : 'border-input'
        }`}
      >
        {placeholder && (
          <option value="" disabled>
            {placeholder}
          </option>
        )}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {error && (
        <span className="text-sm text-destructive mt-1 block">{error.message as string}</span>
      )}
    </div>
  );
}
