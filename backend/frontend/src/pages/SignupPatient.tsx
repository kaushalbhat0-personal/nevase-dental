import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Link, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useAuth } from '../hooks/useAuth';
import {
  patientSignupSchema,
  type PatientSignupFormData,
  type PatientSignupFormInput,
} from '../validation';
import { Button, Card, Input } from '../components/common';
import { postLoginHomePath } from '../utils/roles';

export function SignupPatient() {
  const navigate = useNavigate();
  const { signUp } = useAuth();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<PatientSignupFormInput, unknown, PatientSignupFormData>({
    resolver: zodResolver(patientSignupSchema),
    defaultValues: {
      email: '',
      password: '',
      name: '',
      age: 0,
      gender: '',
      phone: '',
    },
  });

  const onSubmit = async (data: PatientSignupFormData) => {
    const result = await signUp({
      email: data.email,
      password: data.password,
      role: 'patient',
      signup_type: 'patient',
      patient_profile: {
        name: data.name,
        age: data.age,
        gender: data.gender,
        phone: data.phone,
      },
    });
    if (result.success) {
      toast.success('Account created');
      navigate(postLoginHomePath(result.roles ?? ['patient']));
    } else {
      toast.error(result.error || 'Signup failed');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card padding="lg" className="w-full max-w-md">
        <div className="text-center mb-6">
          <h1 className="text-xl font-bold text-text-primary">Patient</h1>
          <p className="text-sm text-text-secondary mt-1">Book appointments with doctors</p>
        </div>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
          <Input label="Email" type="email" error={errors.email?.message} disabled={isSubmitting} {...register('email')} />
          <Input
            label="Password"
            type="password"
            error={errors.password?.message}
            disabled={isSubmitting}
            {...register('password')}
          />
          <Input label="Full name" error={errors.name?.message} disabled={isSubmitting} {...register('name')} />
          <Input label="Age" type="number" error={errors.age?.message} disabled={isSubmitting} {...register('age')} />
          <Input label="Gender" error={errors.gender?.message} disabled={isSubmitting} {...register('gender')} />
          <Input label="Phone" error={errors.phone?.message} disabled={isSubmitting} {...register('phone')} />
          <Button type="submit" variant="primary" size="lg" className="w-full mt-2" isLoading={isSubmitting}>
            Sign up as patient
          </Button>
        </form>
        <p className="mt-6 text-center text-sm text-text-muted">
          <Link to="/login" className="text-primary hover:underline">
            Back to sign in
          </Link>
          {' · '}
          <Link to="/signup" className="text-primary hover:underline">
            Other account types
          </Link>
        </p>
      </Card>
    </div>
  );
}
