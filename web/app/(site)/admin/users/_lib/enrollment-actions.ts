"use server";

import { refresh } from "next/cache";

import {
  ApiError,
  grantAdminEnrollment,
  restoreAdminEnrollment,
  revokeAdminEnrollment,
  type FieldErrors,
} from "@/lib/api";

import { isGrantSource, type EnrollmentActionState } from "./enrollment";

function errorMessage(
  error: unknown,
  verb: "grant" | "revoke" | "restore",
): string {
  if (!(error instanceof ApiError)) {
    return "The course API is not responding, so nothing changed.";
  }
  if (error.status === 400 && typeof error.body === "object" && error.body) {
    const messages = Object.values(error.body as FieldErrors).flat();
    if (messages.length) return messages.join(" ");
  }
  if (error.status === 401 || error.status === 403) {
    return "You no longer have access to the admin area.";
  }
  if (error.status === 404) {
    return verb === "grant"
      ? "This user no longer exists."
      : "This enrollment no longer exists.";
  }
  return `The course API couldn't ${verb} this enrollment. Try again.`;
}

export async function grantEnrollment(
  userId: string,
  _previous: EnrollmentActionState,
  formData: FormData,
): Promise<EnrollmentActionState> {
  const courseId = String(formData.get("course_id") ?? "");
  const source = formData.get("source");
  if (!courseId) return { error: "Choose a course." };
  if (!isGrantSource(source))
    return { courseId, error: "Choose Manual or Comp." };

  try {
    await grantAdminEnrollment(userId, courseId, source);
  } catch (error) {
    return { courseId, source, error: errorMessage(error, "grant") };
  }
  refresh();
  return {};
}

export async function revokeEnrollment(
  id: string,
): Promise<EnrollmentActionState> {
  try {
    await revokeAdminEnrollment(id);
  } catch (error) {
    return { error: errorMessage(error, "revoke") };
  }
  refresh();
  return {};
}

export async function restoreEnrollment(
  id: string,
): Promise<EnrollmentActionState> {
  try {
    await restoreAdminEnrollment(id);
  } catch (error) {
    return { error: errorMessage(error, "restore") };
  }
  refresh();
  return {};
}
