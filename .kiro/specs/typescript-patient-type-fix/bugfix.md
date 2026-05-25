# Bugfix Requirements Document

## Introduction

The frontend TypeScript types for the patient feature are misaligned with the current backend API contract. `CreatePatientData` in `services/patients.ts` still references the old fields (`first_name`, `last_name`, `email`, `date_of_birth`) while the backend now expects `name`, `age`, `gender`, `phone`. Additionally, the Zod schema for `age` uses `z.number()` without coercion, causing a type conflict when the HTML `<input type="number">` returns a string at runtime, and the `patientHandler` passes `PatientFormData` directly to `patientsApi.create` which expects the outdated `CreatePatientData` shape. These mismatches produce TypeScript compilation errors and prevent the build from passing.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN `patientsApi.create` is called with `PatientFormData` THEN the system produces a TypeScript error because `CreatePatientData` expects `{ first_name, last_name, email, date_of_birth }` but receives `{ name, age, gender, phone }`

1.2 WHEN the patient form is submitted with an age value entered by the user THEN the system encounters a type conflict because `patientSchema` uses `z.number()` (no coercion) while the HTML input returns a string, causing `z.infer<typeof patientSchema>` to type `age` as `number` but the runtime value is `unknown`

1.3 WHEN `createPatientHandler` passes `PatientFormData` to `patientsApi.create` THEN the system raises a TypeScript error because the argument type does not satisfy the `CreatePatientData` parameter type

### Expected Behavior (Correct)

2.1 WHEN `patientsApi.create` is called with patient form data THEN the system SHALL accept `{ name: string; age: number; gender: string; phone: string }` matching the current backend API contract

2.2 WHEN the patient form is submitted with an age value THEN the system SHALL coerce the string input to a number via `z.coerce.number()` so that the inferred type is `number` and no type conflict occurs

2.3 WHEN `createPatientHandler` passes `PatientFormData` to `patientsApi.create` THEN the system SHALL compile without errors because both types share the same shape

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a valid patient form is submitted THEN the system SHALL CONTINUE TO call `POST /patients` with the correct payload and display a success toast

3.2 WHEN an invalid patient form is submitted THEN the system SHALL CONTINUE TO display Zod validation errors inline without making an API call

3.3 WHEN the appointments or billing forms use `z.coerce.number()` for their numeric fields THEN the system SHALL CONTINUE TO coerce and validate those fields correctly

3.4 WHEN `FormWrapper`, `FormInput`, and `FormSelect` are used with a typed form THEN the system SHALL CONTINUE TO enforce field name type safety via the `TFieldValues` generic

---

## Bug Condition

```pascal
FUNCTION isBugCondition(X)
  INPUT: X of type { file: string; symbol: string }
  OUTPUT: boolean

  RETURN (X.file = "services/patients.ts" AND X.symbol = "CreatePatientData")
      OR (X.file = "validation/schemas.ts" AND X.symbol = "patientSchema.age" AND uses_z_number_without_coerce(X))
      OR (X.file = "handlers/patientHandler.ts" AND X.symbol = "createPatientHandler" AND arg_type_mismatch(PatientFormData, CreatePatientData))
END FUNCTION
```

```pascal
// Property: Fix Checking
FOR ALL X WHERE isBugCondition(X) DO
  result ← typecheck'(X)
  ASSERT result = no_type_errors
END FOR

// Property: Preservation Checking
FOR ALL X WHERE NOT isBugCondition(X) DO
  ASSERT typecheck(X) = typecheck'(X)
END FOR
```
