# Bugfix Requirements Document

## Introduction

Three interconnected bugs degrade form reliability across the Hospital Management System's
Patients, Appointments, and Billing pages. The most visible symptom is a white screen that
appears after a form is submitted. The root causes are: (1) an unguarded `await refetch()`
call outside the submit `try/catch` block that can throw an unhandled rejection and crash the
component tree; (2) a hard `window.location.href` redirect triggered by the Axios 401
interceptor mid-submit, which tears down the React component tree without a graceful unmount;
and (3) a `FormSelect` double-coercion conflict where `{ valueAsNumber: true }` is applied on
top of Zod's own `z.any().transform()` pipeline, causing `NaN` to reach the validator and
producing silent validation failures or incorrect error messages. Together these issues make
every form in the app unreliable under real-world conditions.

---

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN a form is submitted successfully and the subsequent `refetch()` call throws a network
    or server error THEN the system crashes with an unhandled promise rejection, leaving the
    page as a white screen because the error propagates outside the `try/catch` block in
    `onSubmit`.

1.2 WHEN a form submit request returns HTTP 401 (session expired) THEN the system executes
    `window.location.href = '/login'` inside the Axios response interceptor, forcibly
    navigating away while the React component is still in an async `await`, causing the
    component tree to unmount abruptly and render a white screen before the router can
    transition cleanly.

1.3 WHEN a `FormSelect` field bound to a numeric Zod schema (e.g. `patient_id`, `doctor_id`,
    `amount`) is rendered with an empty initial value THEN the system applies
    `{ valueAsNumber: true }` via `register()` on top of Zod's `z.any().transform()` coercion
    pipeline, converting the empty string `""` to `NaN`, which causes Zod validation to fail
    with an incorrect or missing error message instead of the expected "Please select a
    patient/doctor" message.

1.4 WHEN the `useForm` hook is instantiated in `Appointments.tsx` or `Billing.tsx` without an
    explicit generic type parameter THEN the system loses TypeScript type safety on form field
    names and `onSubmit` data, allowing type errors to go undetected at compile time.

### Expected Behavior (Correct)

2.1 WHEN a form is submitted successfully and the subsequent `refetch()` call throws an error
    THEN the system SHALL catch the refetch error separately, display a non-blocking toast
    notification ("Data refresh failed, please reload"), and keep the page visible without a
    white screen or unhandled rejection.

2.2 WHEN a form submit request returns HTTP 401 THEN the system SHALL allow the current
    `onSubmit` async function to complete its `catch` block, then navigate to `/login` using
    React Router's `navigate()` instead of `window.location.href`, so the component tree
    unmounts gracefully without a white screen.

2.3 WHEN a `FormSelect` field bound to a numeric Zod schema is rendered THEN the system SHALL
    rely solely on Zod's `z.any().transform()` coercion and SHALL NOT pass
    `{ valueAsNumber: true }` to `register()`, so that an empty initial value produces the
    correct "Please select …" validation error instead of a `NaN`-related failure.

2.4 WHEN the `useForm` hook is instantiated in `Appointments.tsx` and `Billing.tsx` THEN the
    system SHALL include the explicit generic type parameter (`useForm<AppointmentFormData>`
    and `useForm<BillingFormData>`) so that TypeScript enforces correct field names and submit
    data types at compile time.

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a form is submitted with valid data and the API call succeeds and `refetch()` also
    succeeds THEN the system SHALL CONTINUE TO show a success toast, reset the form, close the
    form panel, and display the refreshed data list.

3.2 WHEN a form is submitted with invalid data that fails Zod validation THEN the system SHALL
    CONTINUE TO display inline field-level error messages without making any API call.

3.3 WHEN a form is submitted and the API returns a non-401 error (e.g. 422 validation, 500
    server error) THEN the system SHALL CONTINUE TO display the error message in the form's
    `apiError` banner and as a toast notification, keeping the form open with user input
    preserved.

3.4 WHEN a `FormSelect` field has numeric option values and the user selects a valid option
    THEN the system SHALL CONTINUE TO pass the correct numeric value to the Zod schema and
    submit handler.

3.5 WHEN the user's session is valid and no 401 is returned THEN the system SHALL CONTINUE TO
    process form submissions and data fetches normally without any redirect.

3.6 WHEN the `FormInput` component is used with `type="number"` THEN the system SHALL CONTINUE
    TO apply `{ valueAsNumber: true }` via `register()` as this path does not conflict with
    Zod coercion (number inputs do not use the `z.any().transform()` pipeline).

---

## Bug Condition Pseudocode

### Bug Condition Functions

```pascal
FUNCTION isBugCondition_1(X)
  INPUT: X = { submitSucceeds: boolean, refetchThrows: boolean }
  OUTPUT: boolean
  RETURN X.submitSucceeds = true AND X.refetchThrows = true
END FUNCTION

FUNCTION isBugCondition_2(X)
  INPUT: X = { apiResponseStatus: number, componentMounted: boolean }
  OUTPUT: boolean
  RETURN X.apiResponseStatus = 401 AND X.componentMounted = true
END FUNCTION

FUNCTION isBugCondition_3(X)
  INPUT: X = { fieldHasNumericZodSchema: boolean, registerUsesValueAsNumber: boolean, initialValue: string }
  OUTPUT: boolean
  RETURN X.fieldHasNumericZodSchema = true
     AND X.registerUsesValueAsNumber = true
     AND X.initialValue = ""
END FUNCTION
```

### Fix-Checking Properties

```pascal
// Property 1: Refetch error does not crash the page
FOR ALL X WHERE isBugCondition_1(X) DO
  result ← onSubmit'(X)
  ASSERT page_visible(result) = true
  ASSERT unhandled_rejection(result) = false
END FOR

// Property 2: 401 during submit does not produce white screen
FOR ALL X WHERE isBugCondition_2(X) DO
  result ← submitWithInterceptor'(X)
  ASSERT white_screen(result) = false
  ASSERT navigation_method(result) = "react-router"
END FOR

// Property 3: Empty FormSelect with numeric schema shows correct error
FOR ALL X WHERE isBugCondition_3(X) DO
  result ← validateField'(X)
  ASSERT result.error ≠ "NaN" AND result.error ≠ undefined
  ASSERT result.error = "Please select a patient" OR "Please select a doctor"
END FOR
```

### Preservation Property

```pascal
// Preservation: Non-buggy submit flows are unchanged
FOR ALL X WHERE NOT isBugCondition_1(X)
              AND NOT isBugCondition_2(X)
              AND NOT isBugCondition_3(X) DO
  ASSERT F(X) = F'(X)
END FOR
```
