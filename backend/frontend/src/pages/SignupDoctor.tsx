import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Link, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useAuth } from '../hooks/useAuth';
import {
  doctorSignupSchema,
  type DoctorSignupFormData,
  type DoctorSignupFormInput,
} from '../validation';
import { Button, Card, Input } from '../components/common';
import { postLoginHomePath } from '../utils/roles';

export function SignupDoctor() {
  const navigate = useNavigate();
  const { signUp } = useAuth();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<DoctorSignupFormInput, unknown, DoctorSignupFormData>({
    resolver: zodResolver(doctorSignupSchema),
    defaultValues: {
      email: '',
      password: '',
      name: '',
      specialization: '',
      experience_years: 0,
    },
  });

  const onSubmit = async (data: DoctorSignupFormData) => {
    const result = await signUp({
      email: data.email,
      password: data.password,
      role: 'doctor',
      signup_type: 'doctor',
      doctor_profile: {
        name: data.name,
        specialization: data.specialization,
        experience_years: data.experience_years,
      },
    });
    if (result.success) {
      toast.success('Account created');
      navigate(
        postLoginHomePath(result.roles ?? ['doctor'], {
          doctor_id: result.doctor_id,
          doctor_profile_complete: result.doctor_profile_complete,
        })
      );
    } else {
      toast.error(result.error || 'Signup failed');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card padding="lg" className="w-full max-w-md">
        <div className="text-center mb-6">
          <h1 className="text-xl font-bold text-text-primary">Doctor (individual)</h1>
          <p className="text-sm text-text-secondary mt-1">Manage your own practice</p>
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
          <Input
            label="Specialization"
            error={errors.specialization?.message}
            disabled={isSubmitting}
            {...register('specialization')}
          />
          <Input
            label="Years of experience"
            type="number"
            error={errors.experience_years?.message}
            disabled={isSubmitting}
            {...register('experience_years')}
          />
          <Button type="submit" variant="primary" size="lg" className="w-full mt-2" isLoading={isSubmitting}>
            Sign up as doctor
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
