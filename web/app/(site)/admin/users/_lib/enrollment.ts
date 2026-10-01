import type { EnrollmentSource, GrantSource } from "@/lib/api";

/** What the grant form and each row's Revoke or Restore show after submitting. */
export type EnrollmentActionState = {
  error?: string;
  /** The grant form's choices as submitted, so a refused grant keeps them. */
  courseId?: string;
  source?: GrantSource;
};

export const SOURCE_LABELS: Record<EnrollmentSource, string> = {
  purchase: "Purchase",
  manual: "Manual",
  comp: "Comp",
};

export function isGrantSource(value: unknown): value is GrantSource {
  return value === "manual" || value === "comp";
}
