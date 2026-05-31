/**
 * Preservation Property Tests — Property 2
 *
 * Validates: Requirements 3.3, 3.4
 *
 * Baseline behavior for stable schemas:
 * - appointmentSchema: patient_id and doctor_id as non-empty strings (UUIDs from API)
 * - billingSchema: z.coerce.number() for amount
 * - loginSchema: email/password pass-through
 */

import { describe, it, expect } from 'vitest';
import * as fc from 'fast-check';
import { appointmentSchema, billingSchema, loginSchema } from '../schemas';

// A future datetime string (well beyond "now" for test stability)
const FUTURE_DATETIME = '2099-01-01T10:00:00';
const FUTURE_DATE = '2099-12-31';

describe('Preservation: appointmentSchema keeps patient_id and doctor_id as strings', () => {
  it(
    'should preserve UUID strings for patient_id and doctor_id',
    () => {
      /**
       * Property: For all RFC 4122 v4 UUIDs, appointmentSchema preserves string ids.
       *
       * Validates: Requirements 3.3
       */
      fc.assert(
        fc.property(fc.uuid(), fc.uuid(), (patientId, doctorId) => {
          const result = appointmentSchema.parse({
            patient_id: patientId,
            doctor_id: doctorId,
            scheduled_at: FUTURE_DATETIME,
            notes: '',
          });
          expect(typeof result.patient_id).toBe('string');
          expect(typeof result.doctor_id).toBe('string');
          expect(result.patient_id).toBe(patientId);
          expect(result.doctor_id).toBe(doctorId);
        })
      );
    }
  );
});

describe('Preservation: billingSchema coerces amount to number', () => {
  it(
    'should coerce positive numeric string amount to a number',
    () => {
      /**
       * Property: For all positive integers as strings for amount,
       * billingSchema coerces them to numbers.
       *
       * Validates: Requirements 3.3
       */
      fc.assert(
        fc.property(
          fc.integer({ min: 1, max: 999999 }),
          (amount) => {
            const result = billingSchema.parse({
              patient_id: '1',
              amount: String(amount),
              currency: 'INR',
              description: 'Test description',
              due_date: FUTURE_DATE,
            });
            expect(typeof result.amount).toBe('number');
            expect(result.amount).toBe(amount);
          }
        )
      );
    }
  );
});

describe('Preservation: loginSchema parse result is structurally identical', () => {
  it(
    'should return email and password unchanged for valid inputs',
    () => {
      /**
       * Property: For all valid email/password pairs,
       * loginSchema parse result contains the same email and password.
       *
       * Uses a constrained email generator that matches Zod's stricter email regex
       * (alphanumeric local part, standard TLD ≥ 2 chars, no special leading chars).
       *
       * Validates: Requirements 3.4
       */
      // Build a safe email: alphanumeric local@alphanumeric.tld
      const safeEmail = fc
        .tuple(
          fc.stringMatching(/^[A-Za-z0-9]{1,10}$/),
          fc.stringMatching(/^[A-Za-z0-9]{1,10}$/),
          fc.stringMatching(/^[A-Za-z]{2,5}$/)
        )
        .map(([local, domain, tld]) => `${local}@${domain}.${tld}`);

      fc.assert(
        fc.property(
          safeEmail,
          fc.string({ minLength: 1, maxLength: 50 }),
          (email, password) => {
            const result = loginSchema.parse({ email, password });
            expect(result.email).toBe(email);
            expect(result.password).toBe(password);
          }
        )
      );
    }
  );
});
