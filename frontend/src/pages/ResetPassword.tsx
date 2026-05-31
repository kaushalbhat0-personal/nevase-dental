import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import toast from 'react-hot-toast';
import axios from 'axios';
import { useAuth } from '../hooks/useAuth';
import { authApi, formatLoginError } from '../services';
import { getEffectiveRoles, postLoginHomePath } from '../utils/roles';
import { resetPasswordSchema, type ResetPasswordFormData } from '../validation';
import { Button, Card, Input } from '../components/common';

export function ResetPassword() {
  const navigate = useNavigate();
  const { user, patchUser } = useAuth();
  const [apiError, setApiError] = useState('');

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ResetPasswordFormData>({
    resolver: zodResolver(resetPasswordSchema),
  });

  const onSubmit = async (data: ResetPasswordFormData) => {
    setApiError('');
    if (isSubmitting) return;
    try {
      await authApi.resetPassword(data.old_password, data.new_password);
      patchUser({ force_password_reset: false });
      toast.success('Password updated. You are all set.');
      navigate(
        postLoginHomePath(getEffectiveRoles(user, localStorage.getItem('token')), user),
        { replace: true }
      );
    } catch (err) {
      const msg = axios.isAxiosError(err)
        ? formatLoginError(err)
        : 'Could not update password. Please try again.';
      setApiError(msg);
      toast.error(msg, { duration: 5000 });
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card padding="lg" className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="text-6xl mb-4">🔐</div>
          <h1 className="text-2xl font-bold text-text-primary mb-2">Set a new password</h1>
          <p className="text-text-secondary text-sm">
            Your account requires a password change before you can continue.
          </p>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {apiError && (
            <div className="p-3 bg-danger/10 border border-danger/20 rounded-lg text-danger text-sm">
              ⚠️ {apiError}
            </div>
          )}

          <Input
            label="Current password"
            type="password"
            placeholder="Enter your current password"
            error={errors.old_password?.message}
            disabled={isSubmitting}
            autoComplete="current-password"
            {...register('old_password')}
          />

          <Input
            label="New password"
            type="password"
            placeholder="At least 8 characters"
            error={errors.new_password?.message}
            disabled={isSubmitting}
            autoComplete="new-password"
            {...register('new_password')}
          />

          <Input
            label="Confirm new password"
            type="password"
            placeholder="Re-enter new password"
            error={errors.confirm_password?.message}
            disabled={isSubmitting}
            autoComplete="new-password"
            {...register('confirm_password')}
          />

          <Button type="submit" variant="primary" size="lg" isLoading={isSubmitting} className="w-full mt-2">
            Update password
          </Button>
        </form>
      </Card>
    </div>
  );
}
