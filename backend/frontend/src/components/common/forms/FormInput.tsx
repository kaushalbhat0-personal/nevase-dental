import { useFormContext } from 'react-hook-form';
import type { FormInputProps } from './types';

export function FormInput<TFieldValues extends Record<string, unknown>>({
  name,
  label,
  type = 'text',
  placeholder,
  disabled,
  required,
}: FormInputProps<TFieldValues>) {
  const {
    register,
    formState: { errors },
  } = useFormContext<TFieldValues>();

  const error = errors[name];

  // number inputs use valueAsNumber so RHF passes a number to z.number() directly
  // Select/other numeric fields use z.coerce.number() and stay as raw strings
  const registerProps = type === 'number'
    ? register(name, { valueAsNumber: true })
    : register(name);

  const isDate = type === 'date';

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-foreground">
        {label}
        {required && <span className="text-destructive ml-1">*</span>}
      </label>
      <input
        type={type}
        {...registerProps}
        placeholder={placeholder}
        disabled={disabled}
        className={`w-full min-h-[44px] rounded-xl border bg-background px-4 py-2.5 text-foreground transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background ${
          error ? 'border-destructive focus-visible:ring-destructive/30' : 'border-input'
        } ${isDate ? '[color-scheme:light] dark:[color-scheme:dark]' : ''}`}
      />
      {error && (
        <span className="text-sm text-destructive mt-1 block">{error.message as string}</span>
      )}
    </div>
  );
}
