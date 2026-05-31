import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import toast from 'react-hot-toast';
import type { LoginCredentials, LoginResult } from '../types';
import { postLoginHomePath } from '../utils/roles';
import { loginSchema, type LoginFormData } from '../validation';
import { Button, Card, Input } from '../components/common';

interface LoginPageProps {
  onLogin: (credentials: LoginCredentials) => Promise<LoginResult>;
}

export function Login({ onLogin }: LoginPageProps) {
  const [apiError, setApiError] = useState('');
  const navigate = useNavigate();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginFormData) => {
    setApiError('');

    // Prevent double submission
    if (isSubmitting) {
      return;
    }

    try {
      const result = await onLogin({ email: data.email, password: data.password });

      if (result.success) {
        if (result.forcePasswordReset) {
          toast('You must set a new password to continue.', { icon: '🔐', duration: 4000 });
          navigate('/reset-password', { replace: true });
        } else {
          toast.success('Welcome back!', {
            duration: 2000,
            icon: '👋',
          });
          navigate(
            postLoginHomePath(result.roles ?? ['admin'], {
              doctor_id: result.doctor_id,
              doctor_profile_complete: result.doctor_profile_complete,
            })
          );
        }
      } else {
        const errorMessage = result.error || 'Login failed. Please check your credentials and try again.';
        setApiError(errorMessage);
        toast.error(errorMessage, { duration: 5000 });
      }
    } catch {
      const errorMessage = 'An unexpected error occurred. Please try again.';
      setApiError(errorMessage);
      toast.error(errorMessage, { duration: 5000 });
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card padding="lg" className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="text-6xl mb-4">🏥</div>
          <h1 className="text-2xl font-bold text-text-primary mb-2">Nevase Multispecialist Dental Clinic</h1>
          <p className="text-text-secondary">Practice Management System</p>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {apiError && (
            <div className="p-3 bg-danger/10 border border-danger/20 rounded-lg text-danger text-sm">
              ⚠️ {apiError}
            </div>
          )}

          <Input
            label="Email"
            type="email"
            placeholder="admin@hospital.com"
            error={errors.email?.message}
            disabled={isSubmitting}
            {...register('email')}
          />

          <Input
            label="Password"
            type="password"
            placeholder="Enter your password"
            error={errors.password?.message}
            disabled={isSubmitting}
            {...register('password')}
          />

          <Button 
            type="submit" 
            variant="primary"
            size="lg"
            isLoading={isSubmitting}
            className="w-full mt-2"
          >
            Sign In
          </Button>
        </form>

        <div className="mt-8 pt-6 border-t border-border text-center space-y-3">
          <p className="text-sm text-text-muted">
            New here?{' '}
            <Link to="/signup" className="text-primary font-medium hover:underline">
              Create an account
            </Link>
          </p>
          <p className="text-sm text-text-muted mb-2">Demo credentials:</p>
          <code className="text-xs bg-surface-hover px-3 py-1.5 rounded-md text-text-secondary">
            admin@hospital.com / admin123
          </code>
        </div>
      </Card>
    </div>
  );
}
