/**
 * PatientEmergencyProfile.tsx — Emergency Profile page.
 *
 * Patient-visible emergency information:
 * - blood group, allergies, emergency contact
 * - chronic conditions, active medications summary
 * - primary doctor, insurance/provider info placeholder
 *
 * PRESENTATIONAL + editable profile metadata.
 * NO emergency access bypasses, NO QR scanning auth, NO hidden notes.
 */

import { useEffect, useState } from 'react';
import { EmergencyInfoCard } from '@/components/patient/EmergencyInfoCard';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  ArrowLeft,
  HeartPulse,
  Loader2,
  Save,
  AlertTriangle,
  Phone,
  User,
  Stethoscope,
  Shield,
  Plus,
  X,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import {
  getEmergencyProfile,
  updateEmergencyProfile,
} from '@/services/trustAndFamily';
import type { EmergencyProfile, EmergencyProfileUpdate } from '@/types';
import { calmLastUpdated } from '@/utils/trustSignals';

export default function PatientEmergencyProfile() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [profile, setProfile] = useState<EmergencyProfile | null>(null);
  const [editMode, setEditMode] = useState(false);

  // Editable fields
  const [bloodGroup, setBloodGroup] = useState('');
  const [allergies, setAllergies] = useState<string[]>([]);
  const [newAllergy, setNewAllergy] = useState('');
  const [emergencyContactName, setEmergencyContactName] = useState('');
  const [emergencyContactPhone, setEmergencyContactPhone] = useState('');
  const [chronicConditions, setChronicConditions] = useState('');
  const [insuranceProvider, setInsuranceProvider] = useState('');
  const [insuranceId, setInsuranceId] = useState('');

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    setLoading(true);
    try {
      const data = await getEmergencyProfile();
      setProfile(data);
      populateFields(data);
    } catch (err) {
      console.error('Failed to load emergency profile:', err);
    } finally {
      setLoading(false);
    }
  };

  const populateFields = (data: EmergencyProfile) => {
    setBloodGroup(data.blood_group || '');
    setAllergies(data.allergies || []);
    setEmergencyContactName(data.emergency_contact_name || '');
    setEmergencyContactPhone(data.emergency_contact_phone || '');
    setChronicConditions(data.chronic_conditions || '');
    setInsuranceProvider(data.insurance_provider || '');
    setInsuranceId(data.insurance_id || '');
  };

  const addAllergy = () => {
    const trimmed = newAllergy.trim();
    if (trimmed && !allergies.includes(trimmed)) {
      setAllergies([...allergies, trimmed]);
      setNewAllergy('');
    }
  };

  const removeAllergy = (allergy: string) => {
    setAllergies(allergies.filter((a) => a !== allergy));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const update: EmergencyProfileUpdate = {
        blood_group: bloodGroup || null,
        allergies,
        emergency_contact_name: emergencyContactName || null,
        emergency_contact_phone: emergencyContactPhone || null,
        chronic_conditions: chronicConditions || null,
        insurance_provider: insuranceProvider || null,
        insurance_id: insuranceId || null,
      };
      const updated = await updateEmergencyProfile(update);
      setProfile(updated);
      setEditMode(false);
    } catch (err) {
      console.error('Failed to save emergency profile:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    if (profile) {
      populateFields(profile);
    }
    setEditMode(false);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-white border-b border-gray-200">
        <div className="flex items-center justify-between px-4 py-3">
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => navigate(-1)}
              className="text-gray-500"
            >
              <ArrowLeft className="h-5 w-5" />
            </Button>
            <div>
              <h1 className="text-lg font-semibold text-gray-900">
                Emergency Profile
              </h1>
              <p className="text-sm text-gray-500">
                Important health information
              </p>
            </div>
          </div>
          {!editMode ? (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setEditMode(true)}
            >
              Edit
            </Button>
          ) : (
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleCancel}
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={handleSave}
                disabled={saving}
              >
                {saving ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Save className="h-4 w-4 mr-1" />
                )}
                Save
              </Button>
            </div>
          )}
        </div>
      </div>

      <div className="p-4 pb-20 space-y-4">
        {/* Emergency info card (read-only summary) */}
        {profile && !editMode && (
          <EmergencyInfoCard profile={profile} />
        )}

        {/* Disclaimer */}
        <div className="rounded-lg bg-amber-50 border border-amber-200 p-3 flex items-start gap-2">
          <AlertTriangle className="h-4 w-4 text-amber-500 mt-0.5 shrink-0" />
          <p className="text-xs text-amber-700">
            This information helps healthcare providers in emergencies. Keep it
            up to date. It is not a substitute for medical advice.
          </p>
        </div>

        {/* Edit form */}
        {editMode && (
          <div className="space-y-4">
            {/* Blood Group */}
            <div className="space-y-1.5">
              <Label htmlFor="bloodGroup">Blood Group</Label>
              <Input
                id="bloodGroup"
                value={bloodGroup}
                onChange={(e) => setBloodGroup(e.target.value)}
                placeholder="e.g., A+, O-"
              />
            </div>

            {/* Allergies */}
            <div className="space-y-1.5">
              <Label>Allergies</Label>
              <div className="flex flex-wrap gap-1.5 mb-2">
                {allergies.map((allergy) => (
                  <span
                    key={allergy}
                    className="inline-flex items-center gap-1 rounded-full bg-red-50 text-red-700 border border-red-200 px-2.5 py-0.5 text-xs"
                  >
                    {allergy}
                    <button
                      onClick={() => removeAllergy(allergy)}
                      className="text-red-400 hover:text-red-600"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </span>
                ))}
              </div>
              <div className="flex gap-2">
                <Input
                  value={newAllergy}
                  onChange={(e) => setNewAllergy(e.target.value)}
                  placeholder="Add an allergy"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      addAllergy();
                    }
                  }}
                />
                <Button
                  variant="outline"
                  size="icon"
                  onClick={addAllergy}
                  disabled={!newAllergy.trim()}
                >
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
            </div>

            {/* Emergency Contact */}
            <div className="space-y-1.5">
              <Label>Emergency Contact</Label>
              <Input
                value={emergencyContactName}
                onChange={(e) => setEmergencyContactName(e.target.value)}
                placeholder="Contact name"
                className="mb-2"
              />
              <Input
                value={emergencyContactPhone}
                onChange={(e) => setEmergencyContactPhone(e.target.value)}
                placeholder="Contact phone number"
                type="tel"
              />
            </div>

            {/* Chronic Conditions */}
            <div className="space-y-1.5">
              <Label htmlFor="chronicConditions">
                Chronic Conditions
              </Label>
              <Textarea
                id="chronicConditions"
                value={chronicConditions}
                onChange={(e) => setChronicConditions(e.target.value)}
                placeholder="List any chronic conditions (e.g., diabetes, hypertension)"
                rows={3}
              />
            </div>

            {/* Insurance / Provider */}
            <div className="space-y-1.5">
              <Label>Insurance / Provider</Label>
              <Input
                value={insuranceProvider}
                onChange={(e) => setInsuranceProvider(e.target.value)}
                placeholder="Insurance provider name"
                className="mb-2"
              />
              <Input
                value={insuranceId}
                onChange={(e) => setInsuranceId(e.target.value)}
                placeholder="Insurance ID / Policy number"
              />
            </div>
          </div>
        )}

        {/* Read-only display */}
        {!editMode && profile && (
          <div className="space-y-4">
            {/* Blood Group */}
            <div className="rounded-lg border border-gray-200 p-3">
              <div className="flex items-center gap-2 text-sm text-gray-500 mb-1">
                <HeartPulse className="h-4 w-4" />
                Blood Group
              </div>
              <p className="font-medium text-gray-900">
                {profile.blood_group || 'Not specified'}
              </p>
            </div>

            {/* Allergies */}
            <div className="rounded-lg border border-gray-200 p-3">
              <div className="flex items-center gap-2 text-sm text-gray-500 mb-1">
                <AlertTriangle className="h-4 w-4" />
                Allergies
              </div>
              {profile.allergies && profile.allergies.length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {profile.allergies.map((allergy) => (
                    <span
                      key={allergy}
                      className="inline-flex items-center rounded-full bg-red-50 text-red-700 border border-red-200 px-2.5 py-0.5 text-xs"
                    >
                      {allergy}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-500">None listed</p>
              )}
            </div>

            {/* Emergency Contact */}
            <div className="rounded-lg border border-gray-200 p-3">
              <div className="flex items-center gap-2 text-sm text-gray-500 mb-1">
                <Phone className="h-4 w-4" />
                Emergency Contact
              </div>
              {profile.emergency_contact_name ? (
                <div>
                  <p className="font-medium text-gray-900">
                    {profile.emergency_contact_name}
                  </p>
                  {profile.emergency_contact_phone && (
                    <p className="text-sm text-gray-500">
                      {profile.emergency_contact_phone}
                    </p>
                  )}
                </div>
              ) : (
                <p className="text-sm text-gray-500">Not specified</p>
              )}
            </div>

            {/* Chronic Conditions */}
            <div className="rounded-lg border border-gray-200 p-3">
              <div className="flex items-center gap-2 text-sm text-gray-500 mb-1">
                <User className="h-4 w-4" />
                Chronic Conditions
              </div>
              <p className="text-sm text-gray-900">
                {profile.chronic_conditions || 'None listed'}
              </p>
            </div>

            {/* Primary Doctor */}
            {profile.primary_doctor_name && (
              <div className="rounded-lg border border-gray-200 p-3">
                <div className="flex items-center gap-2 text-sm text-gray-500 mb-1">
                  <Stethoscope className="h-4 w-4" />
                  Primary Doctor
                </div>
                <p className="font-medium text-gray-900">
                  {profile.primary_doctor_name}
                </p>
                {profile.primary_doctor_specialization && (
                  <p className="text-sm text-gray-500">
                    {profile.primary_doctor_specialization}
                  </p>
                )}
              </div>
            )}

            {/* Insurance */}
            <div className="rounded-lg border border-gray-200 p-3">
              <div className="flex items-center gap-2 text-sm text-gray-500 mb-1">
                <Shield className="h-4 w-4" />
                Insurance / Provider
              </div>
              {profile.insurance_provider ? (
                <div>
                  <p className="font-medium text-gray-900">
                    {profile.insurance_provider}
                  </p>
                  {profile.insurance_id && (
                    <p className="text-sm text-gray-500">
                      ID: {profile.insurance_id}
                    </p>
                  )}
                </div>
              ) : (
                <p className="text-sm text-gray-500">
                  Not specified
                </p>
              )}
            </div>

            {/* Last updated */}
            {profile.updated_at && (
              <p className="text-xs text-gray-400 text-center">
                {calmLastUpdated(profile.updated_at)}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
