import type { AssignableRole, UserRole } from "@/lib/api";

/** What the role control shows after submitting. */
export type RoleChangeState = {
  error?: string;
  /** Asked for by a Save made without JavaScript: nothing changes until it's confirmed. */
  confirming?: AssignableRole;
};

// The suspension controls point at this line too, rather than repeating it.
export const SELF_HINT_ID = "access-self-hint";

export function isAssignableRole(value: unknown): value is AssignableRole {
  return value === "learner" || value === "admin";
}

/** The confirm step's line naming what the change does. */
export function roleChangeEffect(
  name: string,
  from: UserRole,
  to: AssignableRole,
): string {
  if (to === "admin") {
    return `${name} will be able to manage courses, users, orders, coupons and reviews.`;
  }
  if (from === "admin") return `${name} will lose access to the admin area.`;
  return `${name} will be a learner.`;
}
