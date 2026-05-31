/**
 * Bug Condition Exploration Test — Property 1
 *
 * Validates: Requirements 1.2
 *
 * This test MUST FAIL on unfixed code.
 * Failure confirms the bug exists: patientSchema uses z.number() without coerce,
 * so it rejects string values that come from HTML <input type="number"> at runtime.
 *
 * EXPECTED OUTCOME (on unfixed code):
 *   ZodError: Expected number, received string
 *
 * Once the fix (z.coerce.number()) is applied, this test will PASS.
 */

import { describe, it, expect } from 'vitest';
import * as fc from 'fast-check';
import { patientSchema } from '../schemas';

describe('Bug Condition: patientSchema rejects string age (z.number() without coerce)', () => {
  it(
    'should accept string-encoded integers in [0, 150] as age and return age as a number',
    () => {
      /**
       * Property: For all integers n in [0, 150] converted to strings,
       * patientSchema.parse({ name: "Alice", age: String(n), gender: "male", phone: "0123456789" })
       * should succeed and return age as a number.
       *
       * On UNFIXED code: z.number() rejects strings → ZodError thrown → test FAILS
       * On FIXED code:   z.coerce.number() coerces strings → parse succeeds → test PASSES
       */
      fc.assert(
        fc.property(
          fc.integer({ min: 0, max: 150 }),
          (n) => {
            const result = patientSchema.parse({
              name: 'Alice',
              age: String(n),
              gender: 'male',
              phone: '0123456789',
            });
            expect(typeof result.age).toBe('number');
            expect(result.age).toBe(n);
          }
        )
      );
    }
  );
});
