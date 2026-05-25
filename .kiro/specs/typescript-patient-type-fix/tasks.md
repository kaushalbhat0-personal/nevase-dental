# Implementation Plan

- [x] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - Patient Schema Rejects String Age / CreatePatientData Shape Mismatch
  - **CRITICAL**: This test MUST FAIL on unfixed code — failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior — it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the bug exists
  - **Scoped PBT Approach**: Scope the property to the concrete failing case — `patientSchema.parse({ name: "Alice", age: "25", gender: "male", phone: "0123456789" })` — string age with any valid name/gender/phone
  - Install `vitest` and `@fast-check/vitest` (or `fast-check`) as dev dependencies: `npm install -D vitest fast-check`
  - Add `"test": "vitest --run"` to `scripts` in `package.json`
  - Create `src/validation/__tests__/schemas.bug.test.ts`
  - Write a property-based test using fast-check: for all integers in `[0, 150]` converted to strings, `patientSchema.parse({ name: "Alice", age: String(n), gender: "male", phone: "0123456789" })` should succeed and return `age` as a number — this is the Bug Condition from design (uses `z.number()` without coerce, so it rejects strings)
  - Run `npx vitest --run src/validation/__tests__/schemas.bug.test.ts`
  - **EXPECTED OUTCOME**: Test FAILS with `ZodError: Expected number, received string` (this is correct — it proves the bug exists)
  - Document the counterexample found, e.g. `patientSchema.parse({ age: "25", ... })` throws `ZodError`
  - Mark task complete when test is written, run, and failure is documented
  - _Bug_Condition: isBugCondition(X) where X.file = "validation/schemas.ts" AND X.symbol = "patientSchema.age" AND uses_z_number_without_coerce(X)_
  - _Requirements: 1.2_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Unaffected Schemas Coerce and Validate Correctly
  - **IMPORTANT**: Follow observation-first methodology
  - Observe on UNFIXED code: `appointmentSchema.parse({ patient_id: "1", doctor_id: "2", scheduled_at: "2099-01-01T10:00", notes: "" })` succeeds and returns `patient_id: 1` (number)
  - Observe on UNFIXED code: `billingSchema.parse({ patient_id: "3", amount: "99.99", currency: "INR", description: "Checkup", due_date: "2099-12-31" })` succeeds and returns `amount: 99.99` (number)
  - Observe on UNFIXED code: `loginSchema.parse({ email: "a@b.com", password: "secret" })` succeeds unchanged
  - Create `src/validation/__tests__/schemas.preservation.test.ts`
  - Write property-based tests using fast-check:
    - For all valid `patient_id` and `doctor_id` strings (coercible integers ≥ 1), `appointmentSchema` coerces them to numbers — assert `typeof result.patient_id === "number"`
    - For all positive numeric strings for `amount`, `billingSchema` coerces them to numbers — assert `typeof result.amount === "number"`
    - For all valid email/password pairs, `loginSchema` parse result is structurally identical
  - Run `npx vitest --run src/validation/__tests__/schemas.preservation.test.ts`
  - **EXPECTED OUTCOME**: Tests PASS on UNFIXED code (confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.3, 3.4_

- [-] 3. Fix TypeScript patient type mismatches

  - [x] 3.1 Update `CreatePatientData` in `services/patients.ts`
    - Replace the stale field set with the current backend contract:
      ```ts
      export interface CreatePatientData {
        name: string;
        age: number;
        gender: string;
        phone: string;
      }
      ```
    - Remove `first_name`, `last_name`, `email`, `date_of_birth`, `medical_history` fields
    - _Bug_Condition: isBugCondition(X) where X.file = "services/patients.ts" AND X.symbol = "CreatePatientData" AND fields = { first_name, last_name, email, date_of_birth, phone }_
    - _Expected_Behavior: tsc_check_fixed("services/patients.ts") = no_type_errors_
    - _Preservation: All non-patient API calls and services remain unaffected_
    - _Requirements: 2.1_

  - [x] 3.2 Change `z.number()` to `z.coerce.number()` for `age` in `validation/schemas.ts`
    - Change the `age` field in `patientSchema`:
      ```ts
      age: z.coerce.number({ message: 'Age must be a valid number' }).int().min(0, 'Age must be 0 or greater').max(150, 'Age must be 150 or less'),
      ```
    - No changes to `PatientFormData` type export — it is derived via `z.infer` and updates automatically
    - Do NOT touch `appointmentSchema`, `billingSchema`, or `loginSchema`
    - _Bug_Condition: isBugCondition(X) where X.file = "validation/schemas.ts" AND X.symbol = "patientSchema.age" AND uses_z_number_without_coerce(X)_
    - _Expected_Behavior: patientSchema.parse({ age: "25", ... }).age === 25 (number)_
    - _Preservation: appointmentSchema and billingSchema z.coerce.number() fields continue to coerce correctly_
    - _Requirements: 2.2, 3.3_

  - [x] 3.3 Verify `patientHandler.ts` compiles after type fix
    - Open `handlers/patientHandler.ts` — the direct pass-through `patientsApi.create(data)` where `data: PatientFormData` should now compile without errors because `PatientFormData` and `CreatePatientData` share the same shape
    - No code change is expected; this is a verification step
    - If a TypeScript error still appears, confirm both files were saved and re-run `tsc --noEmit`
    - _Bug_Condition: isBugCondition(X) where X.file = "handlers/patientHandler.ts" AND X.symbol = "createPatientHandler" AND arg_type_mismatch(PatientFormData, CreatePatientData)_
    - _Expected_Behavior: tsc_check_fixed("handlers/patientHandler.ts") = no_type_errors_
    - _Requirements: 2.3_

  - [x] 3.4 Add explicit generics in `pages/Patients.tsx`
    - Confirm `useForm<PatientFormData>({...})` is present (already in file — verify it remains correct after schema fix)
    - Confirm `<FormWrapper<PatientFormData> ...>` is present at the call site (already in file — verify it remains correct)
    - If either generic is missing, add it explicitly
    - _Bug_Condition: isBugCondition(X) where X.file = "pages/Patients.tsx" AND X.symbol = "useForm" AND missing_explicit_generic(X)_
    - _Expected_Behavior: tsc_check_fixed("pages/Patients.tsx") = no_type_errors_
    - _Requirements: 2.1, 2.2, 2.3_

  - [x] 3.5 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Patient Schema Coerces String Age to Number
    - **IMPORTANT**: Re-run the SAME test from task 1 — do NOT write a new test
    - Run `npx vitest --run src/validation/__tests__/schemas.bug.test.ts`
    - **EXPECTED OUTCOME**: Test PASSES (confirms `z.coerce.number()` fix is in effect and string ages are accepted)
    - _Requirements: 2.2_

  - [ ] 3.6 Verify preservation tests still pass
    - **Property 2: Preservation** - Unaffected Schemas Coerce and Validate Correctly
    - **IMPORTANT**: Re-run the SAME tests from task 2 — do NOT write new tests
    - Run `npx vitest --run src/validation/__tests__/schemas.preservation.test.ts`
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions in `appointmentSchema`, `billingSchema`, `loginSchema`)
    - _Requirements: 3.3, 3.4_

- [ ] 4. Checkpoint — Ensure all tests pass and TypeScript compiles clean
  - Run `npx tsc --noEmit` from `backend/frontend/` and confirm exit code 0 with zero errors
  - Run `npx vitest --run` to confirm all schema tests pass
  - Ensure all tests pass; ask the user if questions arise
  - _Requirements: 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 3.4_
