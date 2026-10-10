import type { UserRole } from "@/lib/api";

export const ROLE_LABELS: Record<UserRole, string> = {
  learner: "Learner",
  instructor: "Instructor",
  admin: "Admin",
};
