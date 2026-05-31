import { z } from 'zod';

// Helper to check if date is in the future
const isFutureDate = (dateString: string) => {
  const date = new Date(dateString);
  const now = new Date();
  return date > now;
};

// Helper to check if date is valid (not in the distant past)
const isValidDate = (dateString: string) => {
  const date = new Date(dateString);
  const minDate = new Date('1900-01-01');
  const maxDate = new Date('2100-12-31');
  return date >= minDate && date <= maxDate && !isNaN(date.getTime());
};

// Login form validation
export const loginSchema = z.object({
  email: z
    .string()
    .min(1, 'Email is required')
    .email('Please enter a valid email address'),
  password: z
    .string()
    .min(1, 'Password is required'),
});

// Patient form validation
export const patientSchema = z.object({
  name: z
    .string()
    .min(1, 'Name is required')
    .min(2, 'Name must be at least 2 characters')
    .max(255, 'Name must be less than 255 characters'),
  age: z.coerce.number({ message: 'Age must be a valid number' }).int().min(0, 'Age must be 0 or greater').max(150, 'Age must be 150 or less'),
  gender: z.string().min(1, 'Gender is required'),
  phone: z
    .string()
    .min(1, 'Phone number is required')
    .regex(/^\+?[\d\s-()]{10,}$/, 'Phone number must be at least 10 digits')
    .refine(
      (val) => val.replace(/\D/g, '').length >= 10,
      'Phone number must contain at least 10 digits'
    ),
});

// Appointment form validation
export const appointmentSchema = z.object({
  patient_id: z.string().min(1, 'Please select a patient'),
  doctor_id: z.string().min(1, 'Please select a doctor'),
  scheduled_at: z
    .string()
    .min(1, 'Date and time is required')
    .refine(isValidDate, 'Please enter a valid date and time')
    .refine(isFutureDate, 'Appointment must be scheduled for a future date and time'),
  notes: z
    .string()
    .max(1000, 'Notes must be less than 1000 characters')
    .optional(),
});

// Billing form validation
export const billingSchema = z.object({
  patient_id: z.string().min(1, 'Please select a patient'),
  appointment_id: z.string().optional(), // Optional - backend supports bills without appointments
  amount: z.coerce.number().positive('Amount must be greater than 0').max(999999999.99, 'Amount is too large'),
  currency: z.string().default('INR'),
  description: z
    .string()
    .min(1, 'Description is required')
    .min(3, 'Description must be at least 3 characters')
    .max(200, 'Description must be less than 200 characters'),
  due_date: z
    .string()
    .min(1, 'Due date is required')
    .refine(isValidDate, 'Please enter a valid due date'),
});

// Doctor form validation
export const doctorSchema = z.object({
  name: z
    .string()
    .min(1, 'Name is required')
    .min(2, 'Name must be at least 2 characters')
    .max(255, 'Name must be less than 255 characters'),
  specialization: z.string().min(1, 'Specialization is required'),
  license_number: z.string().optional(),
  experience_years: z.coerce.number().min(0, 'Experience must be 0 or greater').max(100, 'Experience must be 100 or less').optional(),
  account_email: z.string().min(1, 'Email is required').email('Please enter a valid email'),
  account_password: z
    .string()
    .min(1, 'Password is required')
    .min(8, 'Password must be at least 8 characters'),
});

const signupLoginSchema = loginSchema.extend({
  password: z.string().min(8, 'Password must be at least 8 characters'),
});

export const patientSignupSchema = signupLoginSchema.merge(patientSchema);

export const doctorSignupSchema = signupLoginSchema.merge(
  z.object({
    name: z
      .string()
      .min(2, 'Name must be at least 2 characters')
      .max(255, 'Name must be less than 255 characters'),
    specialization: z.string().min(1, 'Specialization is required'),
    experience_years: z.coerce
      .number({ message: 'Experience must be a valid number' })
      .min(0, 'Experience must be 0 or greater')
      .max(100, 'Experience must be 100 or less'),
  })
);

export const hospitalSignupSchema = signupLoginSchema.merge(
  z.object({
    organization_name: z
      .string()
      .min(2, 'Organization name must be at least 2 characters')
      .max(255, 'Name must be less than 255 characters'),
    name: z
      .string()
      .min(2, 'Your name must be at least 2 characters')
      .max(255, 'Name must be less than 255 characters'),
    specialization: z.string().min(1, 'Specialization is required'),
    experience_years: z.coerce
      .number({ message: 'Experience must be a valid number' })
      .min(0, 'Experience must be 0 or greater')
      .max(100, 'Experience must be 100 or less'),
  })
);

/** Mandatory fields aligned with backend `is_profile_complete` (name, phone, spec, reg, qualification). */
export const completeStructuredDoctorProfileSchema = z.object({
  full_name: z.string().min(1, 'Full name is required'),
  phone: z
    .string()
    .min(1, 'Phone is required')
    .transform((val) => val.replace(/\D/g, ''))
    .refine((val) => val.length === 10, {
      message: 'Enter a valid 10-digit phone number',
    }),
  profile_image: z.string().max(2000).optional(),
  specialization: z.string().min(1, 'Specialization is required'),
  experience_years: z.coerce.number().int().min(0).max(80),
  qualification: z.string().min(1, 'Qualification is required').max(2000),
  registration_number: z.string().min(1, 'Registration / license number is required'),
  registration_council: z.string().max(2000).optional(),
  clinic_name: z.string().max(500).optional(),
  address: z.string().max(2000).optional(),
  city: z.string().max(200).optional(),
  state: z.string().max(200).optional(),
});

export const resetPasswordSchema = z
  .object({
    old_password: z.string().min(1, 'Current password is required'),
    new_password: z.string().min(8, 'New password must be at least 8 characters'),
    confirm_password: z.string().min(1, 'Please confirm your new password'),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: 'Passwords do not match',
    path: ['confirm_password'],
  });

// Type exports
export type LoginFormData = z.infer<typeof loginSchema>;
export type PatientFormData = z.infer<typeof patientSchema>;
export type PatientFormInput = z.input<typeof patientSchema>;
export type AppointmentFormData = z.infer<typeof appointmentSchema>;
export type AppointmentFormInput = z.input<typeof appointmentSchema>;
export type BillingFormData = z.infer<typeof billingSchema>;
export type BillingFormInput = z.input<typeof billingSchema>;
export type DoctorFormData = z.infer<typeof doctorSchema>;
export type DoctorFormInput = z.input<typeof doctorSchema>;
export type PatientSignupFormData = z.infer<typeof patientSignupSchema>;
export type PatientSignupFormInput = z.input<typeof patientSignupSchema>;
export type DoctorSignupFormData = z.infer<typeof doctorSignupSchema>;
export type DoctorSignupFormInput = z.input<typeof doctorSignupSchema>;
export type HospitalSignupFormData = z.infer<typeof hospitalSignupSchema>;
export type HospitalSignupFormInput = z.input<typeof hospitalSignupSchema>;
export type ResetPasswordFormData = z.infer<typeof resetPasswordSchema>;
export type CompleteStructuredDoctorProfileFormData = z.infer<typeof completeStructuredDoctorProfileSchema>;
export type CompleteStructuredDoctorProfileFormInput = z.input<typeof completeStructuredDoctorProfileSchema>;
