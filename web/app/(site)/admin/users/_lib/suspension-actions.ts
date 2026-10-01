"use server";

import { refresh } from "next/cache";

import {
  ApiError,
  reinstateAdminUser,
  suspendAdminUser,
  type FieldErrors,
} from "@/lib/api";

import { BLANK_REASON_ERROR, type SuspensionState } from "./suspension";

function errorState(
  error: unknown,
  verb: "suspend" | "reinstate",
): SuspensionState {
  if (!(error instanceof ApiError)) {
    return { error: "The course API is not responding, so nothing changed." };
  }
  if (error.status === 400 && typeof error.body === "object" && error.body) {
    const { reason, non_field_errors } = error.body as FieldErrors;
    return {
      reasonErrors: reason,
      error: non_field_errors?.join(" "),
    };
  }
  if (error.status === 401 || error.status === 403) {
    return { error: "You no longer have access to the admin area." };
  }
  if (error.status === 404) {
    return { error: "This user no longer exists." };
  }
  return { error: `The course API couldn't ${verb} this user. Try again.` };
}

export async function suspendUser(
  id: string,
  _previous: SuspensionState,
  formData: FormData,
): Promise<SuspensionState> {
  const reason = String(formData.get("reason") ?? "").trim();
  if (!reason) return { reason, reasonErrors: [BLANK_REASON_ERROR] };

  try {
    await suspendAdminUser(id, reason);
  } catch (error) {
    return { reason, ...errorState(error, "suspend") };
  }
  refresh();
  return {};
}

export async function reinstateUser(id: string): Promise<SuspensionState> {
  try {
    await reinstateAdminUser(id);
  } catch (error) {
    return errorState(error, "reinstate");
  }
  refresh();
  return {};
}
