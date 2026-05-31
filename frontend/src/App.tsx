import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation, useNavigate, useParams } from 'react-router-dom';
import { useEffect } from 'react';
import { AnimatePresence } from 'framer-motion';
import { Toaster } from 'react-hot-toast';
import { useAuth, AuthProvider } from './hooks/useAuth';
import { AppModeProvider } from './contexts/AppModeContext';
import { initDoctorSlotsCacheCrossTabSync } from './services';
import { setNavigator } from './utils/navigation';
import { getEffectiveRoles, postLoginHomePath } from './utils/roles';
import { RouteIsolation } from './workspace/route-isolation';
import { resolveUserWorkspace } from './workspace/resolver';
import { getLoginRedirectRoute } from './workspace/contextual-redirects';
import AppLayout from './components/layout/AppLayout';
import { ProtectedRoute } from './components/layout/ProtectedRoute';
import { AdminRoute } from './components/layout/AdminRoute';
import { StaffRoute } from './components/layout/StaffRoute';
import { PatientRoute } from './components/layout/PatientRoute';
import { PatientLayout } from './components/layout/PatientLayout';
import { PatientPortalLayout } from './components/layout/PatientPortalLayout';
import { DoctorLayout } from './components/layout/DoctorLayout';
import { DoctorRoute } from './components/layout/DoctorRoute';
import { AnimatedPage } from './animations';

/* ──────────────────────────────────────────────
 * Lazy-loaded page components
 * ────────────────────────────────────────────── */

// Public pages
const PublicLayout = lazy(() => import('./pages/public/PublicLayout'));
const PublicHome = lazy(() => import('./pages/public/HomePage'));
const PublicServices = lazy(() => import('./pages/public/ServicesPage'));
const PublicDoctors = lazy(() => import('./pages/public/DoctorsPage'));
const PublicContact = lazy(() => import('./pages/public/ContactPage'));
const PublicBookAppointment = lazy(() => import('./pages/public/BookAppointmentPage'));

// Auth pages
const Login = lazy(() => import('./pages/Login').then(m => ({ default: m.Login })));
const Signup = lazy(() => import('./pages/Signup').then(m => ({ default: m.Signup })));
const SignupPatient = lazy(() => import('./pages/SignupPatient').then(m => ({ default: m.SignupPatient })));
const SignupDoctor = lazy(() => import('./pages/SignupDoctor').then(m => ({ default: m.SignupDoctor })));
const ResetPassword = lazy(() => import('./pages/ResetPassword').then(m => ({ default: m.ResetPassword })));

// Staff / Admin pages
const Dashboard = lazy(() => import('./pages/Dashboard').then(m => ({ default: m.Dashboard })));
const Patients = lazy(() => import('./pages/Patients').then(m => ({ default: m.Patients })));
const Doctors = lazy(() => import('./pages/Doctors').then(m => ({ default: m.Doctors })));
const Appointments = lazy(() => import('./pages/Appointments').then(m => ({ default: m.Appointments })));
const Billing = lazy(() => import('./pages/Billing').then(m => ({ default: m.Billing })));
const AdminDashboard = lazy(() => import('./pages/AdminDashboard').then(m => ({ default: m.AdminDashboard })));
const AdminInventoryPage = lazy(() => import('./pages/InventoryPage').then(m => ({ default: m.AdminInventoryPage })));
const AdminBrandingPage = lazy(() => import('./pages/AdminBrandingPage').then(m => ({ default: m.default })));
const AdminCommunicationsPage = lazy(() => import('./pages/AdminCommunicationsPage').then(m => ({ default: m.default })));

// Doctor pages
const DoctorHome = lazy(() => import('./pages/doctor/DoctorHome').then(m => ({ default: m.DoctorHome })));
const DoctorDoctorsPage = lazy(() => import('./pages/doctor/DoctorDoctorsPage').then(m => ({ default: m.DoctorDoctorsPage })));
const DoctorPatientsPage = lazy(() => import('./pages/doctor/DoctorPatientsPage').then(m => ({ default: m.DoctorPatientsPage })));
const DoctorPatientDetailPage = lazy(() => import('./pages/doctor/DoctorPatientDetailPage').then(m => ({ default: m.DoctorPatientDetailPage })));
const DoctorAppointmentsPage = lazy(() => import('./pages/doctor/DoctorAppointmentsPage').then(m => ({ default: m.DoctorAppointmentsPage })));
const EncounterWorkspacePage = lazy(() => import('./pages/doctor/EncounterWorkspacePage').then(m => ({ default: m.EncounterWorkspacePage })));
const DoctorBillsPage = lazy(() => import('./pages/doctor/DoctorBillsPage').then(m => ({ default: m.DoctorBillsPage })));
const DoctorBillDetailPage = lazy(() => import('./pages/doctor/DoctorBillDetailPage').then(m => ({ default: m.DoctorBillDetailPage })));
const DoctorAvailabilityPage = lazy(() => import('./pages/doctor/DoctorAvailabilityPage').then(m => ({ default: m.DoctorAvailabilityPage })));
const PatientInventory = lazy(() => import('./pages/doctor/PatientInventory').then(m => ({ default: m.PatientInventory })));
const ClinicOnboardingPage = lazy(() => import('./pages/doctor/ClinicOnboardingPage').then(m => ({ default: m.ClinicOnboardingPage })));
const CompleteProfilePage = lazy(() => import('./pages/doctor/CompleteProfilePage').then(m => ({ default: m.CompleteProfilePage })));

// Patient pages (existing)
const PatientHome = lazy(() => import('./pages/patient/PatientHome').then(m => ({ default: m.PatientHome })));
const PatientCareHub = lazy(() => import('./pages/patient/PatientCareHub').then(m => ({ default: m.PatientCareHub })));
const PatientDiscover = lazy(() => import('./pages/patient/PatientDiscover').then(m => ({ default: m.PatientDiscover })));
const PatientProfile = lazy(() => import('./pages/patient/PatientProfile').then(m => ({ default: m.PatientProfile })));
const PatientProfileSettings = lazy(() => import('./pages/patient/PatientProfileSettings').then(m => ({ default: m.PatientProfileSettings })));
const PatientClinicDoctors = lazy(() => import('./pages/patient/PatientClinicDoctors').then(m => ({ default: m.PatientClinicDoctors })));
const PatientAppointments = lazy(() => import('./pages/patient/PatientAppointments').then(m => ({ default: m.PatientAppointments })));
const PatientBills = lazy(() => import('./pages/patient/PatientBills').then(m => ({ default: m.PatientBills })));
const PatientDoctorDetail = lazy(() => import('./pages/patient/PatientDoctorDetail').then(m => ({ default: m.PatientDoctorDetail })));
const PatientHealthTimeline = lazy(() => import('./pages/patient/PatientHealthTimeline').then(m => ({ default: m.PatientHealthTimeline })));
const PatientEncounterDetail = lazy(() => import('./pages/patient/PatientEncounterDetail').then(m => ({ default: m.PatientEncounterDetail })));
const PatientVitalsHistory = lazy(() => import('./pages/patient/PatientVitalsHistory').then(m => ({ default: m.PatientVitalsHistory })));
const PatientFollowUps = lazy(() => import('./pages/patient/PatientFollowUps').then(m => ({ default: m.PatientFollowUps })));
const PatientCommunicationCenter = lazy(() => import('./pages/patient/PatientCommunicationCenter').then(m => ({ default: m.PatientCommunicationCenter })));
const PatientDocuments = lazy(() => import('./pages/patient/PatientDocuments').then(m => ({ default: m.PatientDocuments })));
const PatientMedicines = lazy(() => import('./pages/patient/PatientMedicines').then(m => ({ default: m.PatientMedicines })));
const PatientFamilyHub = lazy(() => import('./pages/patient/PatientFamilyHub').then(m => ({ default: m.default })));
const PatientEmergencyProfile = lazy(() => import('./pages/patient/PatientEmergencyProfile').then(m => ({ default: m.default })));

// Patient portal pages (new)
const PatientDashboard = lazy(() => import('./pages/patient/PatientDashboard'));
const PatientPrescriptions = lazy(() => import('./pages/patient/PatientPrescriptions'));
const PatientMedications = lazy(() => import('./pages/patient/PatientMedications'));

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const warmUpBackend = async () => {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);

    await fetch(`${API_BASE_URL}/health`, {
      method: 'GET',
      signal: controller.signal,
    });

    clearTimeout(timeoutId);
    console.log('[App] Backend warmed up successfully');
  } catch (err) {
    console.log('[App] Backend warmup call failed (may be cold starting):', err);
  }
};

/**
 * Lightweight Suspense fallback — not a blocking full-screen spinner.
 * Just a subtle indicator while the chunk loads.
 */
function PageFallback() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary/20 border-t-primary" />
    </div>
  );
}

/**
 * Redirect wrapper components for backward-compatible routes.
 * These use useParams to properly interpolate route params into the target URL,
 * avoiding the bug where literal ":appointmentId" strings were sent to the API.
 */
function RedirectEncounterDetail() {
  const { appointmentId } = useParams<{ appointmentId: string }>();
  return <Navigate to={`/patient/care/encounters/${appointmentId}`} replace />;
}

function RedirectDoctorDetail() {
  const { id } = useParams<{ id: string }>();
  return <Navigate to={`/patient/discover/doctor/${id}`} replace />;
}

function RedirectDoctorDetailByDoctorId() {
  const { doctorId } = useParams<{ doctorId: string }>();
  return <Navigate to={`/patient/discover/doctor/${doctorId}`} replace />;
}

function RedirectClinicDetail() {
  const { tenantId } = useParams<{ tenantId: string }>();
  return <Navigate to={`/patient/discover/clinic/${tenantId}`} replace />;
}

function AnimatedRoutes() {
  const { user, isAuthenticated, isLoading, login, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    setNavigator(navigate);
  }, [navigate]);

  const token = localStorage.getItem('token');
  const effectiveRoles = getEffectiveRoles(user, token);
  const needsPasswordReset = user?.force_password_reset === true;
  const resolvedWorkspace = resolveUserWorkspace(user, token);
  const loginRedirect = needsPasswordReset
    ? '/reset-password'
    : getLoginRedirectRoute(resolvedWorkspace, location.pathname);

  if (
    !isLoading &&
    isAuthenticated &&
    needsPasswordReset &&
    location.pathname !== '/reset-password'
  ) {
    return <Navigate to="/reset-password" replace />;
  }

  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        {/* Public website pages (no auth required) - root level */}
        <Route element={<Suspense fallback={<PageFallback />}><PublicLayout /></Suspense>}>
          <Route path="/" element={<PublicHome />} />
          <Route path="/services" element={<PublicServices />} />
          <Route path="/doctors" element={<PublicDoctors />} />
          <Route path="/contact" element={<PublicContact />} />
          <Route path="/book" element={<PublicBookAppointment />} />
        </Route>

        {/* Backward-compatible redirects from /clinic/* to root */}
        <Route path="/clinic" element={<Navigate to="/" replace />} />
        <Route path="/clinic/services" element={<Navigate to="/services" replace />} />
        <Route path="/clinic/doctors" element={<Navigate to="/doctors" replace />} />
        <Route path="/clinic/contact" element={<Navigate to="/contact" replace />} />
        <Route path="/clinic/book-appointment" element={<Navigate to="/book" replace />} />

        <Route
          path="/login"
          element={
            isLoading ? (
              <div className="min-h-screen flex flex-col items-center justify-center gap-3 bg-background">
                <div className="spinner" />
                <p className="text-sm text-muted-foreground">Loading…</p>
              </div>
            ) : isAuthenticated ? (
              <Navigate to={loginRedirect} replace />
            ) : (
              <Suspense fallback={<PageFallback />}>
                <Login onLogin={login} />
              </Suspense>
            )
          }
        />

        <Route
          path="/signup"
          element={
            isLoading ? (
              <div className="min-h-screen flex flex-col items-center justify-center gap-3 bg-background">
                <div className="spinner" />
                <p className="text-sm text-muted-foreground">Loading…</p>
              </div>
            ) : isAuthenticated ? (
              <Navigate to={loginRedirect} replace />
            ) : (
              <Suspense fallback={<PageFallback />}>
                <Signup />
              </Suspense>
            )
          }
        />

        <Route
          path="/signup/patient"
          element={
            isLoading ? (
              <div className="min-h-screen flex flex-col items-center justify-center gap-3 bg-background">
                <div className="spinner" />
                <p className="text-sm text-muted-foreground">Loading…</p>
              </div>
            ) : isAuthenticated ? (
              <Navigate to={loginRedirect} replace />
            ) : (
              <Suspense fallback={<PageFallback />}>
                <SignupPatient />
              </Suspense>
            )
          }
        />

        <Route
          path="/signup/doctor"
          element={
            isLoading ? (
              <div className="min-h-screen flex flex-col items-center justify-center gap-3 bg-background">
                <div className="spinner" />
                <p className="text-sm text-muted-foreground">Loading…</p>
              </div>
            ) : isAuthenticated ? (
              <Navigate to={loginRedirect} replace />
            ) : (
              <Suspense fallback={<PageFallback />}>
                <SignupDoctor />
              </Suspense>
            )
          }
        />

        <Route
          path="/reset-password"
          element={
            <ProtectedRoute isAuthenticated={isAuthenticated} isLoading={isLoading}>
              {isAuthenticated && !needsPasswordReset ? (
                <Navigate to={postLoginHomePath(effectiveRoles, user)} replace />
              ) : (
                <Suspense fallback={<PageFallback />}>
                  <ResetPassword />
                </Suspense>
              )}
            </ProtectedRoute>
          }
        />

        <Route
          path="/complete-profile"
          element={
            <ProtectedRoute isAuthenticated={isAuthenticated} isLoading={isLoading}>
              <Suspense fallback={<PageFallback />}>
                <CompleteProfilePage />
              </Suspense>
            </ProtectedRoute>
          }
        />

        <Route path="/create-tenant" element={<Navigate to="/onboarding/clinic" replace />} />

        <Route
          path="/onboarding/clinic"
          element={
            <ProtectedRoute isAuthenticated={isAuthenticated} isLoading={isLoading}>
              <DoctorRoute user={user}>
                <AnimatedPage>
                  <Suspense fallback={<PageFallback />}>
                    <ClinicOnboardingPage />
                  </Suspense>
                </AnimatedPage>
              </DoctorRoute>
            </ProtectedRoute>
          }
        />

        <Route
          path="/dashboard"
          element={
            <ProtectedRoute isAuthenticated={isAuthenticated} isLoading={isLoading}>
              <StaffRoute user={user}>
                <AppLayout user={user} onLogout={logout}>
                  <AnimatedPage>
                    <Suspense fallback={<PageFallback />}>
                      <Dashboard />
                    </Suspense>
                  </AnimatedPage>
                </AppLayout>
              </StaffRoute>
            </ProtectedRoute>
          }
        />

        {/* Backward-compatible redirect: bare /admin → admin dashboard landing */}
        <Route
          path="/admin"
          element={<Navigate to="/admin/dashboard" replace />}
        />

        <Route
          path="/admin/dashboard"
          element={
            <ProtectedRoute isAuthenticated={isAuthenticated} isLoading={isLoading}>
              <StaffRoute user={user}>
                <AdminRoute user={user}>
                  <AppLayout user={user} onLogout={logout}>
                    <AnimatedPage>
                      <Suspense fallback={<PageFallback />}>
                        <AdminDashboard />
                      </Suspense>
                    </AnimatedPage>
                  </AppLayout>
                </AdminRoute>
              </StaffRoute>
            </ProtectedRoute>
          }
        />

        <Route
          path="/admin/inventory"
          element={
            <ProtectedRoute isAuthenticated={isAuthenticated} isLoading={isLoading}>
              <StaffRoute user={user}>
                <AdminRoute user={user}>
                  <AppLayout user={user} onLogout={logout}>
                    <AnimatedPage>
                      <Suspense fallback={<PageFallback />}>
                        <AdminInventoryPage />
                      </Suspense>
                    </AnimatedPage>
                  </AppLayout>
                </AdminRoute>
              </StaffRoute>
            </ProtectedRoute>
          }
        />

        <Route
          path="/admin/branding"
          element={
            <ProtectedRoute isAuthenticated={isAuthenticated} isLoading={isLoading}>
              <StaffRoute user={user}>
                <AdminRoute user={user}>
                  <AppLayout user={user} onLogout={logout}>
                    <AnimatedPage>
                      <Suspense fallback={<PageFallback />}>
                        <AdminBrandingPage />
                      </Suspense>
                    </AnimatedPage>
                  </AppLayout>
                </AdminRoute>
              </StaffRoute>
            </ProtectedRoute>
          }
        />

        <Route
          path="/admin/communications"
          element={
            <ProtectedRoute isAuthenticated={isAuthenticated} isLoading={isLoading}>
              <StaffRoute user={user}>
                <AdminRoute user={user}>
                  <AppLayout user={user} onLogout={logout}>
                    <AnimatedPage>
                      <Suspense fallback={<PageFallback />}>
                        <AdminCommunicationsPage />
                      </Suspense>
                    </AnimatedPage>
                  </AppLayout>
                </AdminRoute>
              </StaffRoute>
            </ProtectedRoute>
          }
        />

        <Route
          path="/patients"
          element={
            <ProtectedRoute isAuthenticated={isAuthenticated} isLoading={isLoading}>
              <StaffRoute user={user}>
                <AppLayout user={user} onLogout={logout}>
                  <AnimatedPage>
                    <Suspense fallback={<PageFallback />}>
                      <Patients />
                    </Suspense>
                  </AnimatedPage>
                </AppLayout>
              </StaffRoute>
            </ProtectedRoute>
          }
        />

        <Route
          path="/doctors"
          element={
            <ProtectedRoute isAuthenticated={isAuthenticated} isLoading={isLoading}>
              <StaffRoute user={user}>
                <AppLayout user={user} onLogout={logout}>
                  <AnimatedPage>
                    <Suspense fallback={<PageFallback />}>
                      <Doctors />
                    </Suspense>
                  </AnimatedPage>
                </AppLayout>
              </StaffRoute>
            </ProtectedRoute>
          }
        />

        <Route
          path="/appointments"
          element={
            <ProtectedRoute isAuthenticated={isAuthenticated} isLoading={isLoading}>
              <StaffRoute user={user}>
                <AppLayout user={user} onLogout={logout}>
                  <AnimatedPage>
                    <Suspense fallback={<PageFallback />}>
                      <Appointments />
                    </Suspense>
                  </AnimatedPage>
                </AppLayout>
              </StaffRoute>
            </ProtectedRoute>
          }
        />

        <Route
          path="/billing"
          element={
            <ProtectedRoute isAuthenticated={isAuthenticated} isLoading={isLoading}>
              <StaffRoute user={user}>
                <AppLayout user={user} onLogout={logout}>
                  <AnimatedPage>
                    <Suspense fallback={<PageFallback />}>
                      <Billing />
                    </Suspense>
                  </AnimatedPage>
                </AppLayout>
              </StaffRoute>
            </ProtectedRoute>
          }
        />

        <Route
          path="/doctor"
          element={
            <ProtectedRoute isAuthenticated={isAuthenticated} isLoading={isLoading}>
              <DoctorRoute user={user}>
                <RouteIsolation workspaceSlug="doctor">
                  <DoctorLayout />
                </RouteIsolation>
              </DoctorRoute>
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="dashboard" replace />} />
          <Route path="home" element={<Navigate to="/doctor/dashboard" replace />} />
          <Route
            path="dashboard"
            element={
              <AnimatedPage>
                <Suspense fallback={<PageFallback />}>
                  <DoctorHome />
                </Suspense>
              </AnimatedPage>
            }
          />
          <Route
            path="doctors"
            element={
              <AnimatedPage>
                <Suspense fallback={<PageFallback />}>
                  <DoctorDoctorsPage />
                </Suspense>
              </AnimatedPage>
            }
          />
          <Route
            path="patients"
            element={
              <AnimatedPage>
                <Suspense fallback={<PageFallback />}>
                  <DoctorPatientsPage />
                </Suspense>
              </AnimatedPage>
            }
          />
          <Route
            path="patients/:id"
            element={
              <AnimatedPage>
                <Suspense fallback={<PageFallback />}>
                  <DoctorPatientDetailPage />
                </Suspense>
              </AnimatedPage>
            }
          />
          {/*
            Encounter Workspace - Future-proof clinical workspace for patient visits
            Replaces the legacy DoctorAppointmentDetailPage with encounter-centric architecture
            that supports Phase 2 clinical features (prescriptions, vitals, SOAP notes, etc.)
          */}
          <Route
            path="appointments/:appointmentId"
            element={
              <AnimatedPage>
                <Suspense fallback={<PageFallback />}>
                  <EncounterWorkspacePage />
                </Suspense>
              </AnimatedPage>
            }
          />
          {/* Legacy route preserved for backward compatibility - redirects to workspace */}
          <Route
            path="encounter/:appointmentId"
            element={
              <AnimatedPage>
                <Suspense fallback={<PageFallback />}>
                  <EncounterWorkspacePage />
                </Suspense>
              </AnimatedPage>
            }
          />
          <Route
            path="appointments"
            element={
              <AnimatedPage>
                <Suspense fallback={<PageFallback />}>
                  <DoctorAppointmentsPage />
                </Suspense>
              </AnimatedPage>
            }
          />
          <Route
            path="bills/:billId"
            element={
              <AnimatedPage>
                <Suspense fallback={<PageFallback />}>
                  <DoctorBillDetailPage />
                </Suspense>
              </AnimatedPage>
            }
          />
          <Route
            path="bills"
            element={
              <AnimatedPage>
                <Suspense fallback={<PageFallback />}>
                  <DoctorBillsPage />
                </Suspense>
              </AnimatedPage>
            }
          />
          <Route
            path="availability"
            element={
              <AnimatedPage>
                <Suspense fallback={<PageFallback />}>
                  <DoctorAvailabilityPage />
                </Suspense>
              </AnimatedPage>
            }
          />
          <Route
            path="inventory"
            element={
              <AnimatedPage>
                <Suspense fallback={<PageFallback />}>
                  <PatientInventory />
                </Suspense>
              </AnimatedPage>
            }
          />
        </Route>

        {/* Patient portal routes (sidebar layout) */}
        <Route
          element={
            <ProtectedRoute isAuthenticated={isAuthenticated} isLoading={isLoading}>
              <PatientRoute user={user}>
                <PatientPortalLayout />
              </PatientRoute>
            </ProtectedRoute>
          }
        >
          <Route path="/patient/dashboard" element={
            <AnimatedPage>
              <Suspense fallback={<PageFallback />}>
                <PatientDashboard />
              </Suspense>
            </AnimatedPage>
          } />
          <Route path="/patient/appointments" element={
            <AnimatedPage>
              <Suspense fallback={<PageFallback />}>
                <PatientAppointments />
              </Suspense>
            </AnimatedPage>
          } />
          <Route path="/patient/bills" element={
            <AnimatedPage>
              <Suspense fallback={<PageFallback />}>
                <PatientBills />
              </Suspense>
            </AnimatedPage>
          } />
          <Route path="/patient/prescriptions" element={
            <AnimatedPage>
              <Suspense fallback={<PageFallback />}>
                <PatientPrescriptions />
              </Suspense>
            </AnimatedPage>
          } />
          <Route path="/patient/medications" element={
            <AnimatedPage>
              <Suspense fallback={<PageFallback />}>
                <PatientMedications />
              </Suspense>
            </AnimatedPage>
          } />
        </Route>

        <Route
          path="/patient"
          element={
            <ProtectedRoute isAuthenticated={isAuthenticated} isLoading={isLoading}>
              <PatientRoute user={user}>
                <PatientLayout />
              </PatientRoute>
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="home" replace />} />

          {/* ── HOME ─────────────────────────────────────────────────────── */}
          <Route
            path="home"
            element={
              <AnimatedPage>
                <Suspense fallback={<PageFallback />}>
                  <PatientHome />
                </Suspense>
              </AnimatedPage>
            }
          />

          {/* ── CARE HUB ─────────────────────────────────────────────────── */}
          <Route path="care" element={<PatientCareHub />}>
            <Route index element={<Navigate to="timeline" replace />} />
            <Route
              path="timeline"
              element={
                <AnimatedPage>
                  <Suspense fallback={<PageFallback />}>
                    <PatientHealthTimeline />
                  </Suspense>
                </AnimatedPage>
              }
            />
            <Route
              path="medicines"
              element={
                <AnimatedPage>
                  <Suspense fallback={<PageFallback />}>
                    <PatientMedicines />
                  </Suspense>
                </AnimatedPage>
              }
            />
            <Route
              path="vitals"
              element={
                <AnimatedPage>
                  <Suspense fallback={<PageFallback />}>
                    <PatientVitalsHistory />
                  </Suspense>
                </AnimatedPage>
              }
            />
            <Route
              path="follow-ups"
              element={
                <AnimatedPage>
                  <Suspense fallback={<PageFallback />}>
                    <PatientFollowUps />
                  </Suspense>
                </AnimatedPage>
              }
            />
            <Route
              path="encounters/:appointmentId"
              element={
                <AnimatedPage>
                  <Suspense fallback={<PageFallback />}>
                    <PatientEncounterDetail />
                  </Suspense>
                </AnimatedPage>
              }
            />
          </Route>

          {/* ── MESSAGES ─────────────────────────────────────────────────── */}
          <Route
            path="messages"
            element={
              <AnimatedPage>
                <Suspense fallback={<PageFallback />}>
                  <PatientCommunicationCenter />
                </Suspense>
              </AnimatedPage>
            }
          />

          {/* ── DISCOVER ─────────────────────────────────────────────────── */}
          <Route
            path="discover"
            element={
              <AnimatedPage>
                <Suspense fallback={<PageFallback />}>
                  <PatientDiscover />
                </Suspense>
              </AnimatedPage>
            }
          />
          <Route
            path="discover/doctor/:id"
            element={
              <AnimatedPage>
                <Suspense fallback={<PageFallback />}>
                  <PatientDoctorDetail />
                </Suspense>
              </AnimatedPage>
            }
          />
          <Route
            path="discover/clinic/:tenantId"
            element={
              <AnimatedPage>
                <Suspense fallback={<PageFallback />}>
                  <PatientClinicDoctors />
                </Suspense>
              </AnimatedPage>
            }
          />

          {/* ── PROFILE ──────────────────────────────────────────────────── */}
          <Route path="profile" element={<PatientProfile />}>
            <Route index element={<Navigate to="documents" replace />} />
            <Route
              path="documents"
              element={
                <AnimatedPage>
                  <Suspense fallback={<PageFallback />}>
                    <PatientDocuments />
                  </Suspense>
                </AnimatedPage>
              }
            />
            <Route
              path="bills"
              element={
                <AnimatedPage>
                  <Suspense fallback={<PageFallback />}>
                    <PatientBills />
                  </Suspense>
                </AnimatedPage>
              }
            />
            <Route
              path="appointments"
              element={
                <AnimatedPage>
                  <Suspense fallback={<PageFallback />}>
                    <PatientAppointments />
                  </Suspense>
                </AnimatedPage>
              }
            />
            <Route
              path="settings"
              element={
                <AnimatedPage>
                  <Suspense fallback={<PageFallback />}>
                    <PatientProfileSettings />
                  </Suspense>
                </AnimatedPage>
              }
            />
          </Route>

          {/* ── TRUST & FAMILY ───────────────────────────────────────────── */}
          <Route
            path="family"
            element={
              <AnimatedPage>
                <Suspense fallback={<PageFallback />}>
                  <PatientFamilyHub />
                </Suspense>
              </AnimatedPage>
            }
          />
          <Route
            path="emergency-profile"
            element={
              <AnimatedPage>
                <Suspense fallback={<PageFallback />}>
                  <PatientEmergencyProfile />
                </Suspense>
              </AnimatedPage>
            }
          />

          {/* ── BACKWARD-COMPATIBLE REDIRECTS ────────────────────────────── */}
          {/* Old primary tab routes → new locations */}
          <Route path="timeline" element={<Navigate to="/patient/care/timeline" replace />} />
          <Route path="medicines" element={<Navigate to="/patient/care/medicines" replace />} />
          <Route path="vitals" element={<Navigate to="/patient/care/vitals" replace />} />
          <Route path="follow-ups" element={<Navigate to="/patient/care/follow-ups" replace />} />
          <Route path="encounters/:appointmentId" element={<RedirectEncounterDetail />} />
          <Route path="communications" element={<Navigate to="/patient/messages" replace />} />
          <Route path="doctors" element={<Navigate to="/patient/discover" replace />} />
          <Route path="doctor/:id" element={<RedirectDoctorDetail />} />
          <Route path="doctors/:doctorId" element={<RedirectDoctorDetailByDoctorId />} />
          <Route path="clinic/:tenantId" element={<RedirectClinicDetail />} />
          <Route path="documents" element={<Navigate to="/patient/profile/documents" replace />} />
          <Route path="bills" element={<Navigate to="/patient/profile/bills" replace />} />
          <Route path="appointments" element={<Navigate to="/patient/profile/appointments" replace />} />
        </Route>



      </Routes>
    </AnimatePresence>
  );
}

function App() {
  useEffect(() => {
    warmUpBackend();
  }, []);
  useEffect(() => {
    return initDoctorSlotsCacheCrossTabSync();
  }, []);

  return (
    <BrowserRouter>
      <AuthProvider>
        <AppModeProvider>
          <AnimatedRoutes />
        </AppModeProvider>
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 4000,
            style: {
              background: '#ffffff',
              color: '#0f172a',
              border: '1px solid #e2e8f0',
              boxShadow: '0 10px 15px -3px rgba(15, 23, 42, 0.08)',
            },
            success: {
              duration: 3000,
              iconTheme: {
                primary: '#10B981',
                secondary: 'white',
              },
            },
            error: {
              duration: 5000,
              iconTheme: {
                primary: '#EF4444',
                secondary: 'white',
              },
            },
          }}
        />
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
