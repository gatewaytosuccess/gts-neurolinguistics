"use server";

import { refresh } from "next/cache";

import {
  ApiError,
  updateAdminUserRole,
  type FieldErrors,
  type UserRole,
} from "@/lib/api";

import { isAssignableRole, type RoleChangeState } from "./role-change";

function roleErrorMessage(error: unknown): string {
  if (!(error instanceof ApiError)) {
    return "The course API is not responding, so nothing changed.";
  }
  if (error.status === 400 && typeof error.body === "object" && error.body) {
    const { role = [], non_field_errors = [] } = error.body as FieldErrors;
    const messages = [...role, ...non_field_errors];
    if (messages.length) return messages.join(" ");
  }
  if (error.status === 401 || error.status === 403) {
    return "You no longer have access to the admin area.";
  }
  if (error.status === 404) return "This user no longer exists.";
  return "The course API couldn't change this role. Try again.";
}

export async function changeUserRole(
  id: string,
  currentRole: UserRole,
  _previous: RoleChangeState,
  formData: FormData,
): Promise<RoleChangeState> {
  const role = formData.get("role");
  if (!isAssignableRole(role)) return { error: "Choose Learner or Admin." };
  if (role === currentRole) return {};

  // With JavaScript the dialog has already confirmed; without it, Save lands here first.
  if (formData.get("confirmed") !== "yes") return { confirming: role };

  try {
    await updateAdminUserRole(id, role);
  } catch (error) {
    return { error: roleErrorMessage(error) };
  }
  refresh();
  return {};
}
