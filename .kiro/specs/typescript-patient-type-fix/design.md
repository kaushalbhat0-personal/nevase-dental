# TypeScript Patient Type Fix — Bugfix Design

## Overview

The patient feature has three interconnected TypeScript type mismatches that prevent the build from compiling:

1. `CreatePatientData` in `services/patients.ts` still references the old backend fields (`first_name`, `last_name`, `email`, `date_of_birth`) while the backend now expects `{ name, age, gender, phone }`.
2. `patientSchema` in `validation/schemas.ts` uses `z.number()` (no coercion) for `age`, but an HTML `<input type="number">` returns a string at runtime, causing a type conflict.
3. `createPatientHandler` passes `PatientFormData` directly to `patientsApi.create`, which still expects the outdated `CreatePatientData` shape.

Two secondary issues also exist:
- `useForm` calls in `Patients.tsx` lack an explicit generic (`useForm<PatientFormData>()`), relying on inference that breaks when the schema type is wrong.
- `FormWrapper` is already generic but the explicit generic is not always passed at call sites.

The fix is minimal and targeted: update the type definition, fix the Zod schema, remove the stale field mapping in the handler, and add the missing explicit generics. No runtime logic changes are required beyond the coercion fix.

---

## Glossary

- **Bug_Condition (C)**: A source location + symbol pair where the current TypeScript types are misaligned with the backend contract or with each other.
- **Property (P)**: The desired post-fix state — `tsc --noEmit` exits with zero errors for all affected symbols.
- **Preservation**: All runtime behaviour for valid and invalid form submissions, API calls, and unrelated form schemas must remain identical after the fix.
- **`CreatePatientData`**: The interface in `services/patients.ts` that describes the payload sent to `POST /patients`.
- **`patientSchema`**: The Zod object schema in `validation/schemas.ts` that validates the patient creation form.
- **`PatientFormData`**: The type derived from `patientSchema` via `z.infer<typeof patientSchema>`.
- **`createPatientHandler`**: The function in `handlers/patientHandler.ts` that calls `patientsApi.create`.
- **`useForm<T>`**: The react-hook-form hook; without an explicit generic the inferred type may not match the resolver's output type.
- **`FormWrapper<TFieldValues>`**: The generic form container component; the generic must be passed explicitly at call sites for full type safety.

---

## Bug Details

### Bug Condition

The bug manifests at compile time across three files. The TypeScript compiler rejects the call `patientsApi.create(data)` in `patientHandler.ts` because `PatientFormData` (`{ name, age, gender, phone }`) does not satisfy `CreatePatientData` (`{ first_name, last_name, email, date_of_birth, phone }`). Additionally, `z.number()` without coercion means the inferred type for `age` is `number`, but the HTML input delivers a string, causing a hidden runtime mismatch even when TypeScript is satisfied.

**Formal Specification:**

```
FUNCTION isBugCondition(X)
  INPUT: X of type { file: string; symbol: string }
  OUTPUT: boolean

  RETURN (X.file = "services/patients.ts"
          AND X.symbol = "CreatePatientData"
          AND fields(X.symbol) = { first_name, last_name, email, date_of_birth, phone })
      OR (X.file = "validation/schemas.ts"
          AND X.symbol = "patientSchema.age"
          AND uses_z_number_without_coerce(X.symbol))
      OR (X.file = "handlers/patientHandler.ts"
          AND X.symbol = "createPatientHandler"
          AND arg_type_mismatch(PatientFormData, CreatePatientData))
      OR (X.file = "pages/Patients.tsx"
          AND X.symbol = "useForm"
          AND missing_explicit_generic(X.symbol))
END FUNCTION
```

### Examples

- **Example 1 — `CreatePatientData` mismatch**: `patientsApi.create({ name: 'Alice', age: 30, gender: 'female', phone: '0123456789' })` → TypeScript error: _Object literal may only specify known properties, and 'name' does not exist in type 'CreatePatientData'_.
- **Example 2 — `z.number()` coercion gap**: User types `"25"` into the age input → `patientSchema.parse({ ..., age: "25" })` throws a Zod validation error at runtime even though the field appears valid, because `z.number()` rejects strings.
- **Example 3 — handler type mismatch**: `createPatientHandler(data)` where `data: PatientFormData` → TypeScript error: _Argument of type 'PatientFormData' is not assignable to parameter of type 'CreatePatientData'_.
- **Edge case — `useForm` without generic**: Without `useForm<PatientFormData>()`, TypeScript infers a looser type, masking field-name errors in `FormInput` and `FormSelect` usages.

---

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- A valid patient form submission MUST continue to call `POST /patients` with the correct payload and display a success toast.
- An invalid patient form submission MUST continue to display Zod validation errors inline without making an API call.
- The `appointmentSchema` and `billingSchema` already use `z.coerce.number()` and MUST continue to coerce and validate their numeric fields correctly — they are not touched by this fix.
- `FormWrapper`, `FormInput`, and `FormSelect` generic behaviour MUST continue to enforce field-name type safety via `TFieldValues`.
- All other pages (Appointments, Billing, etc.) MUST be completely unaffected.

**Scope:**
All inputs that do NOT involve the patient creation form or the `CreatePatientData` / `patientSchema` symbols are outside the bug condition and must be fully preserved. This includes:
- Mouse clicks, keyboard navigation, and touch interactions on any form.
- All non-patient API calls.
- All other Zod schemas (`loginSchema`, `appointmentSchema`, `billingSchema`).

---

## Hypothesized Root Cause

1. **Stale type definition**: `CreatePatientData` was never updated when the backend patient model was refactored from a multi-field model (`first_name`, `last_name`, `email`, `date_of_birth`) to a simpler one (`name`, `age`, `gender`, `phone`). The frontend service layer was left behind.

2. **Missing Zod coercion**: `patientSchema.age` uses `z.number()` instead of `z.coerce.number()`. Every other numeric field in the codebase (`patient_id`, `doctor_id`, `amount`) already uses `z.coerce.number()`, so this is an oversight — likely the schema was written before the coercion pattern was established.

3. **Direct pass-through in handler**: `createPatientHandler` passes `PatientFormData` directly to `patientsApi.create` without any field mapping. This was probably intentional (avoiding unnecessary transformation), but it only compiles correctly when both types share the same shape — which they currently do not.

4. **Missing explicit generics**: `useForm` without `<PatientFormData>` and `FormWrapper` without the explicit generic at call sites are minor issues that become visible once the underlying type mismatch is resolved. They do not cause errors on their own but reduce type safety.

---

## Correctness Properties

Property 1: Bug Condition — TypeScript Compilation Succeeds for Patient Types

_For any_ source location X where `isBugCondition(X)` is true (i.e., `CreatePatientData`, `patientSchema.age`, `createPatientHandler`, or `useForm` without generic), the fixed codebase SHALL produce zero TypeScript compiler errors at that location, and `tsc --noEmit` SHALL exit with code 0.

**Validates: Requirements 2.1, 2.2, 2.3**

Property 2: Preservation — Unaffected Symbols Remain Type-Correct

_For any_ source location X where `isBugCondition(X)` is false (i.e., all symbols outside the four affected locations), the fixed codebase SHALL produce the same TypeScript diagnostics as the original codebase — no new errors introduced, no existing passing checks broken.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4**

---

## Fix Implementation

### Changes Required

**File 1: `backend/frontend/src/services/patients.ts`**

**Symbol**: `CreatePatientData`

**Specific Changes**:
1. Replace the old field set with the new backend contract:
   ```ts
   // Before
   export interface CreatePatientData {
     first_name: string;
     last_name: string;
     email: string;
     phone: string;
     date_of_birth: string;
     medical_history?: string;
   }

   // After
   export interface CreatePatientData {
     name: string;
     age: number;
     gender: string;
     phone: string;
   }
   ```

---

**File 2: `backend/frontend/src/validation/schemas.ts`**

**Symbol**: `patientSchema.age`

**Specific Changes**:
1. Change `z.number(...)` to `z.coerce.number(...)` so HTML string inputs are coerced before validation:
   ```ts
   // Before
   age: z.number({ message: 'Age must be a valid number' }).int().min(0, ...).max(150, ...),

   // After
   age: z.coerce.number({ message: 'Age must be a valid number' }).int().min(0, ...).max(150, ...),
   ```
2. No changes needed to `PatientFormData` — it is already derived via `z.infer<typeof patientSchema>` and will automatically reflect the corrected type.

---

**File 3: `backend/frontend/src/handlers/patientHandler.ts`**

**Symbol**: `createPatientHandler`

**Specific Changes**:
1. No field mapping is needed — after fixing `CreatePatientData` to match `PatientFormData`, the direct pass-through `patientsApi.create(data)` is already correct. No code change is required in this file beyond confirming the types now align. (If the TypeScript error disappears after fixing files 1 and 2, this file needs no edit.)

---

**File 4: `backend/frontend/src/pages/Patients.tsx`**

**Symbol**: `useForm`

**Specific Changes**:
1. Add explicit generic to `useForm`:
   ```ts
   // Before
   const form = useForm({
   // After
   const form = useForm<PatientFormData>({
   ```
   _(Note: the file already has `useForm<PatientFormData>` — verify during implementation whether this is already present or still missing.)_

---

**File 5: `backend/frontend/src/components/common/forms/FormWrapper.tsx`** _(call sites)_

**Symbol**: `FormWrapper` usage in `Patients.tsx`

**Specific Changes**:
1. Ensure the explicit generic is passed at the call site:
   ```tsx
   // Before (if missing)
   <FormWrapper form={form} ...>
   // After
   <FormWrapper<PatientFormData> form={form} ...>
   ```
   _(Note: `Patients.tsx` already shows `<FormWrapper<PatientFormData>` — verify during implementation.)_

---

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the type errors on the unfixed code (exploratory), then verify the fix eliminates all errors and preserves existing behaviour.

Because the bug is a compile-time type error, the primary validation tool is `tsc --noEmit`. Runtime behaviour is validated through unit and integration tests.

---

### Exploratory Bug Condition Checking

**Goal**: Confirm the root cause by observing TypeScript errors on the unfixed code before applying any changes.

**Test Plan**: Run `tsc --noEmit` on the unfixed codebase and capture the exact error messages. This confirms which symbols are affected and validates the root cause hypothesis.

**Test Cases**:
1. **`CreatePatientData` mismatch**: Observe TS error when `patientsApi.create(data)` is called with `PatientFormData` (will fail on unfixed code).
2. **`z.number()` coercion gap**: Write a unit test that calls `patientSchema.parse({ name: 'Alice', age: '25', gender: 'male', phone: '0123456789' })` and assert it succeeds — this will fail on unfixed code because `z.number()` rejects the string `"25"`.
3. **Handler type mismatch**: Observe TS error in `patientHandler.ts` at the `patientsApi.create(data)` call site (will fail on unfixed code).
4. **Missing generic**: Observe whether `useForm` without explicit generic produces a type error or looser inference (may or may not fail depending on TS strictness).

**Expected Counterexamples**:
- `tsc --noEmit` reports errors in `services/patients.ts`, `handlers/patientHandler.ts`, and possibly `pages/Patients.tsx`.
- `patientSchema.parse({ age: "25", ... })` throws `ZodError` with message "Expected number, received string".

---

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed code produces the expected behaviour (zero type errors, correct runtime coercion).

**Pseudocode:**
```
FOR ALL X WHERE isBugCondition(X) DO
  result := tsc_check_fixed(X)
  ASSERT result = no_type_errors
END FOR

// Runtime coercion check
result := patientSchema_fixed.parse({ name: "Alice", age: "25", gender: "male", phone: "0123456789" })
ASSERT result.age = 25          // number, not string
ASSERT typeof result.age = "number"
```

---

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed code produces the same result as the original code.

**Pseudocode:**
```
FOR ALL X WHERE NOT isBugCondition(X) DO
  ASSERT tsc_check_original(X) = tsc_check_fixed(X)
END FOR

// Runtime preservation
FOR ALL schema IN [loginSchema, appointmentSchema, billingSchema] DO
  FOR ALL validInput IN validInputsFor(schema) DO
    ASSERT schema.parse(validInput) = schema_fixed.parse(validInput)
  END FOR
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many valid and invalid inputs automatically across the input domain.
- It catches edge cases (boundary ages, special characters in phone numbers) that manual tests miss.
- It provides strong guarantees that unaffected schemas behave identically before and after the fix.

**Test Plan**: Observe that `appointmentSchema`, `billingSchema`, and `loginSchema` parse correctly on the unfixed code, then write property-based tests asserting identical parse results after the fix.

**Test Cases**:
1. **`appointmentSchema` preservation**: Generate random valid appointment inputs and assert parse results are identical before and after fix.
2. **`billingSchema` preservation**: Generate random valid billing inputs and assert parse results are identical.
3. **`loginSchema` preservation**: Generate random email/password pairs and assert parse results are identical.
4. **Valid patient submission preservation**: After fix, a valid form submission MUST still call `POST /patients` and show a success toast.
5. **Invalid patient submission preservation**: After fix, an invalid form submission MUST still show inline Zod errors without making an API call.

---

### Unit Tests

- Test `patientSchema.parse` with a string age (`"25"`) — must succeed and return `age: 25` (number) after fix.
- Test `patientSchema.parse` with an out-of-range age (`-1`, `151`) — must still fail with the correct error message.
- Test `patientSchema.parse` with a missing required field — must still fail.
- Test `patientsApi.create` type signature accepts `{ name, age, gender, phone }` without TypeScript errors.
- Test `createPatientHandler` compiles without errors when passed `PatientFormData`.

### Property-Based Tests

- Generate random integers in `[0, 150]` as strings and assert `patientSchema` coerces them to numbers correctly.
- Generate random integers outside `[0, 150]` and assert `patientSchema` rejects them.
- Generate random valid inputs for `appointmentSchema` and `billingSchema` and assert parse results are unchanged by the fix (preservation).
- Generate random `PatientFormData`-shaped objects and assert `createPatientHandler` accepts them without type errors.

### Integration Tests

- Submit the patient creation form with valid data and assert `POST /patients` is called with `{ name, age, gender, phone }` (not the old fields).
- Submit the patient creation form with an age entered as a string (simulating browser input) and assert the form submits successfully after coercion.
- Submit the patient creation form with invalid data and assert no API call is made and errors are displayed.
- Verify the appointments and billing forms continue to submit correctly after the fix.
