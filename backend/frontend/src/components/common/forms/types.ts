import type { ReactNode } from 'react';
import type { FieldPath, FieldValues, UseFormReturn } from 'react-hook-form';

export interface FormFieldProps<TFieldValues extends FieldValues = FieldValues> {
  name: FieldPath<TFieldValues>;
  label: string;
  disabled?: boolean;
  required?: boolean;
}

export interface FormInputProps<TFieldValues extends FieldValues = FieldValues>
  extends FormFieldProps<TFieldValues> {
  type?: 'text' | 'email' | 'password' | 'tel' | 'number' | 'date' | 'datetime-local';
  placeholder?: string;
}

export interface FormSelectOption {
  value: string | number;
  label: string;
}

export interface FormSelectProps<TFieldValues extends FieldValues = FieldValues>
  extends FormFieldProps<TFieldValues> {
  options: FormSelectOption[];
  placeholder?: string;
}

export interface FormTextareaProps<TFieldValues extends FieldValues = FieldValues>
  extends FormFieldProps<TFieldValues> {
  placeholder?: string;
  rows?: number;
}

export interface FormDatePickerProps<TFieldValues extends FieldValues = FieldValues>
  extends FormFieldProps<TFieldValues> {
  placeholder?: string;
  min?: string;
  max?: string;
}

export interface FormWrapperProps<TFieldValues extends FieldValues = FieldValues, TTransformedValues extends FieldValues = TFieldValues> {
  form: UseFormReturn<TFieldValues, any, TTransformedValues>;
  onSubmit: (data: TTransformedValues) => Promise<void> | void;
  children: ReactNode;
  submitLabel?: string;
  loadingLabel?: string;
  className?: string;
  apiError?: string;
}
