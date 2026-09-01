/**
 * Case ID derivation.
 *
 * A case id is an ENTITY IDENTIFIER, not a display-order number. It must be
 * derived from the case's own identity (the numeric part of user_id) so the
 * same case shows the same id on every page and API, regardless of how the
 * queue is sorted, filtered or paginated.
 *
 * Regression guarded by tests/caseId.test.ts:
 * the original bug built ids from queue position ("CASE-00001" for the
 * first row of the risk-sorted queue), so every case was relabelled
 * whenever scores changed page or ordering.
 */

/** Extract the stable identity part of a user id. */
export function caseIdentity(userId: string | null | undefined): string {
  if (!userId) return 'UNKNOWN';
  const digits = userId.replace(/\D/g, '');
  // A user_id without digits keeps its raw id as the case handle — still
  // identity-based and stable; never a list position.
  return digits || userId;
}

/** Derive the display Case ID for a case from its user identity. */
export function caseIdFromUser(userId: string | null | undefined): string {
  return `CASE-${caseIdentity(userId)}`;
}
