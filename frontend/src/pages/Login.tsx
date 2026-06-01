import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import toast from 'react-hot-toast';
import type { LoginCredentials, LoginResult } from '../types';
import { postLoginHomePath } from '../utils/roles';
import { loginSchema, type LoginFormData } from '../validation';
import { Button, Card, Input } from '../components/common';
import { ArrowLeft } from 'lucide-react';

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

    if (isSubmitting) return;

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
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-sky-50 via-white to-white p-4">
      <Card padding="lg" className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="w-16 h-16 rounded-2xl bg-[#0EA5E9] flex items-center justify-center mx-auto mb-4 shadow-lg shadow-[#0EA5E9]/20">
            <span className="text-white font-bold text-3xl">N</span>
          </div>
          <h1 className="text-xl font-bold text-[#0F172A] mb-1">Nevase's Multispeciality Dental Clinic</h1>
          <p className="text-sm text-[#1E293B]/60">Staff & Patient Portal</p>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {apiError && (
            <div className="p-3 bg-danger/10 border border-danger/20 rounded-lg text-danger text-sm">
              ⚠️ {apiError}
            </div>
          )}

          <Input
            label="Email or phone"
            type="text"
            placeholder="admin@hospital.com or 9876543210"
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
          <div className="flex items-center justify-center gap-2 text-xs text-text-muted">
            <span className="bg-surface-hover px-2.5 py-1 rounded-md">admin@hospital.com</span>
            <span className="text-text-muted/50">/</span>
            <span className="bg-surface-hover px-2.5 py-1 rounded-md">admin123</span>
          </div>
          <Link to="/" className="inline-flex items-center gap-1.5 text-sm text-primary font-medium hover:underline mt-2">
            <ArrowLeft className="w-3.5 h-3.5" />
            Back to Website
          </Link>
        </div>
      </Card>
    </div>
  );
}
