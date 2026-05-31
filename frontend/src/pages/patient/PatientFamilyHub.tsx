/**
 * PatientFamilyHub.tsx — Family & Trust Hub page.
 *
 * Central page for family/dependent management, trusted contacts,
 * caregiver access, and shared care awareness.
 *
 * FOUNDATION ONLY — no auth delegation, no permission escalation.
 */

import { useEffect, useState } from 'react';
import { PageSection } from '@/components/ui/page-section';
import { DependentProfileCard } from '@/components/patient/DependentProfileCard';
import { CaregiverAccessCard } from '@/components/patient/CaregiverAccessCard';
import { TrustedContactsSection } from '@/components/patient/TrustedContactsSection';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Users,
  Heart,
  Shield,
  ArrowLeft,
  Loader2,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import {
  getDependents,
  getCaregivers,
  getTrustedContacts,
} from '@/services/trustAndFamily';
import type { DependentProfile, CaregiverAccess, TrustedContact } from '@/types';

export default function PatientFamilyHub() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [dependents, setDependents] = useState<DependentProfile[]>([]);
  const [caregivers, setCaregivers] = useState<CaregiverAccess[]>([]);
  const [trustedContacts, setTrustedContacts] = useState<TrustedContact[]>([]);
  const [activeTab, setActiveTab] = useState('family');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [deps, cares, contacts] = await Promise.all([
        getDependents(),
        getCaregivers(),
        getTrustedContacts(),
      ]);
      setDependents(deps);
      setCaregivers(cares);
      setTrustedContacts(contacts);
    } catch (err) {
      console.error('Failed to load family data:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-white border-b border-gray-200">
        <div className="flex items-center gap-3 px-4 py-3">
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
              Family & Trust
            </h1>
            <p className="text-sm text-gray-500">
              Care managed together
            </p>
          </div>
        </div>
      </div>

      <div className="p-4 pb-20">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
          </div>
        ) : (
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="w-full mb-4">
              <TabsTrigger value="family" className="flex-1">
                <Heart className="h-4 w-4 mr-1" />
                Family
              </TabsTrigger>
              <TabsTrigger value="contacts" className="flex-1">
                <Users className="h-4 w-4 mr-1" />
                Contacts
              </TabsTrigger>
              <TabsTrigger value="caregivers" className="flex-1">
                <Shield className="h-4 w-4 mr-1" />
                Caregivers
              </TabsTrigger>
            </TabsList>

            {/* ═══════════════════════════════════════════════════════
               TAB 1: FAMILY / DEPENDENTS
               ═══════════════════════════════════════════════════════ */}
            <TabsContent value="family" className="space-y-4">
              <PageSection
                title="Family Members"
                description="People you care for who are linked to your account."
              >
                {dependents.length > 0 ? (
                  <div className="space-y-3">
                    {dependents.map((dep) => (
                      <DependentProfileCard
                        key={dep.id}
                        dependent={dep}
                        onSwitchProfile={(id) => {
                          // TODO: Phase 2 — Switch active patient profile
                          console.log('Switch to dependent:', id);
                        }}
                      />
                    ))}
                  </div>
                ) : (
                  <div className="rounded-lg border border-dashed border-gray-300 p-6 text-center">
                    <Heart className="mx-auto h-8 w-8 text-gray-300" />
                    <p className="mt-2 text-sm text-gray-500">
                      No family members linked yet.
                    </p>
                    <p className="text-xs text-gray-400 mt-1">
                      You'll be able to add family members here in a future update.
                    </p>
                    {/* TODO: Phase 2 — Add dependent flow */}
                    {/* <Button variant="outline" size="sm" className="mt-3">
                      <UserPlus className="h-4 w-4 mr-1" />
                      Add Family Member
                    </Button> */}
                  </div>
                )}
              </PageSection>

              {/* Family-aware care indicators */}
              {dependents.length > 0 && (
                <PageSection
                  title="Family Care Overview"
                  description="Quick view of your family's upcoming care needs."
                >
                  <div className="space-y-2">
                    {dependents.map((dep) => (
                      <div
                        key={dep.id}
                        className="rounded-lg border border-gray-200 p-3"
                      >
                        <div className="flex items-center gap-2">
                          <Heart className="h-4 w-4 text-rose-400" />
                          <span className="font-medium text-gray-900">
                            {dep.name}
                          </span>
                        </div>
                        {dep.upcoming_appointments && dep.upcoming_appointments.length > 0 && (
                          <p className="mt-1 text-sm text-gray-500">
                            Your child's upcoming visit:{' '}
                            {dep.upcoming_appointments[0].doctor_name}
                          </p>
                        )}
                        {dep.shared_medication_count > 0 && (
                          <p className="text-sm text-gray-500">
                            Shared medication reminder:{' '}
                            {dep.shared_medication_count} medication{dep.shared_medication_count !== 1 ? 's' : ''}
                          </p>
                        )}
                        <p className="text-xs text-gray-400 mt-1">
                          Care managed together
                        </p>
                      </div>
                    ))}
                  </div>
                </PageSection>
              )}
            </TabsContent>

            {/* ═══════════════════════════════════════════════════════
               TAB 2: TRUSTED CONTACTS
               ═══════════════════════════════════════════════════════ */}
            <TabsContent value="contacts">
              <TrustedContactsSection
                contacts={trustedContacts}
                onEditContact={(id) => {
                  // TODO: Phase 2 — Edit trusted contact
                  console.log('Edit contact:', id);
                }}
              />
            </TabsContent>

            {/* ═══════════════════════════════════════════════════════
               TAB 3: CAREGIVERS
               ═══════════════════════════════════════════════════════ */}
            <TabsContent value="caregivers" className="space-y-4">
              <PageSection
                title="Caregivers with Access"
                description="People who can help manage your care."
              >
                {caregivers.length > 0 ? (
                  <div className="space-y-3">
                    {caregivers.map((cg) => (
                      <CaregiverAccessCard
                        key={cg.id}
                        caregiver={cg}
                      />
                    ))}
                  </div>
                ) : (
                  <div className="rounded-lg border border-dashed border-gray-300 p-6 text-center">
                    <Shield className="mx-auto h-8 w-8 text-gray-300" />
                    <p className="mt-2 text-sm text-gray-500">
                      No caregivers have access yet.
                    </p>
                    <p className="text-xs text-gray-400 mt-1">
                      You'll be able to invite caregivers in a future update.
                    </p>
                    {/* TODO: Phase 2 — Invite caregiver flow */}
                    {/* <Button variant="outline" size="sm" className="mt-3">
                      <UserPlus className="h-4 w-4 mr-1" />
                      Invite Caregiver
                    </Button> */}
                  </div>
                )}
              </PageSection>
            </TabsContent>
          </Tabs>
        )}
      </div>
    </div>
  );
}
