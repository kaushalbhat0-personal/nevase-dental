import { Navigate, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useAuth } from '../../hooks/useAuth';
import { doctorProfileApi } from '../../services';
import { Button, Card, Input } from '../../components/common';

export function CompleteProfilePage() {
  const { user, isLoading, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  if (isLoading) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-3 bg-background">
        <div className="spinner" />
        <p className="text-sm text-text-secondary">Loading…</p>
      </div>
    );
  }
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  if (!user?.doctor_id) {
    return null;
  }

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <div className="flex-1 overflow-y-auto p-4 pb-28 flex justify-center">
        <Card padding="lg" className="w-full max-w-2xl">
          <h1 className="text-xl font-bold text-text-primary mb-1">Complete your profile</h1>
          <p className="text-sm text-text-secondary mb-4">
            Add your details so patients can identify you. You can update these anytime.
          </p>
          <form
            id="complete-profile-form"
            onSubmit={async (e) => {
              e.preventDefault();
              const form = e.currentTarget;
              const data = {
                full_name: (form.elements.namedItem('full_name') as HTMLInputElement)?.value ?? '',
                phone: (form.elements.namedItem('phone') as HTMLInputElement)?.value ?? '',
                specialization: (form.elements.namedItem('specialization') as HTMLInputElement)?.value ?? '',
                bio: (form.elements.namedItem('bio') as HTMLInputElement)?.value ?? '',
              };
              try {
                await doctorProfileApi.put(data);
                await doctorProfileApi.submitForVerification();
                toast.success('Profile saved');
                navigate('/doctor/dashboard', { replace: true });
              } catch {
                toast.error('Failed to save profile');
              }
            }}
            className="space-y-6"
          >
            <Input label="Full name" name="full_name" placeholder="e.g. Dr. Sayali Nevase" required />
            <Input label="Phone" name="phone" placeholder="e.g. 9876543210" required />
            <Input label="Specialization" name="specialization" placeholder="e.g. Dentist" required />
            <Input label="Bio (optional)" name="bio" placeholder="Short bio about yourself" />
            <Button type="submit" variant="primary" size="lg" className="w-full">
              Save Profile
            </Button>
          </form>
        </Card>
      </div>
    </div>
  );
}
