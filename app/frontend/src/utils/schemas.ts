import { z } from 'zod';

export const wellIdSchema = z
  .string()
  .trim()
  .min(1, 'Well ID is required for manual entry')
  .regex(
    /^[A-Za-z0-9][A-Za-z0-9_.\-]*$/,
    'Well ID may only contain letters, numbers, underscore, dot, or hyphen',
  );

export const optionalWellIdSchema = z
  .string()
  .trim()
  .refine(
    (value) => value === '' || wellIdSchema.safeParse(value).success,
    'Well ID may only contain letters, numbers, underscore, dot, or hyphen',
  );

export function validateOptionalWellId(value: string): string | null {
  const result = optionalWellIdSchema.safeParse(value);
  if (result.success) {
    return null;
  }
  return result.error.issues[0]?.message ?? 'Invalid well ID';
}

export function validateManualWellId(value: string): string | null {
  const result = wellIdSchema.safeParse(value);
  if (result.success) {
    return null;
  }
  return result.error.issues[0]?.message ?? 'Invalid well ID';
}
