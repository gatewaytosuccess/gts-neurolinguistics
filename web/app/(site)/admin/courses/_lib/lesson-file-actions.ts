"use server";

import { refresh } from "next/cache";

import {
  ApiError,
  requestAdminLessonUpload,
  updateAdminLesson,
  type AdminLessonInput,
  type FieldErrors,
  type LessonFileKind,
} from "@/lib/api";

import type { UploadResult, UploadTicket } from "./uploads";

function errorMessage(error: unknown): string {
  if (!(error instanceof ApiError)) {
    return "The course API is not responding, so nothing changed.";
  }
  // Also covers a `publishProblems` body: its one entry is the list of problems.
  if (error.status === 400 && typeof error.body === "object" && error.body) {
    return Object.values(error.body as FieldErrors)
      .flat()
      .join(" ");
  }
  if (error.status === 401 || error.status === 403) {
    return "You no longer have access to the admin area.";
  }
  if (error.status === 404) {
    return "This lesson no longer exists.";
  }
  return "The course API couldn't change this file. Try again.";
}

export async function requestLessonUpload(
  lessonId: string,
  kind: LessonFileKind,
): Promise<UploadTicket> {
  try {
    return { upload: await requestAdminLessonUpload(lessonId, kind) };
  } catch (error) {
    return { error: errorMessage(error) };
  }
}

/**
 * A blank `key` removes the file. `durationSeconds` is saved with it when
 * given; `undefined` leaves the lesson's duration as it is.
 */
export async function saveLessonFile(
  lessonId: string,
  kind: LessonFileKind,
  key: string,
  durationSeconds?: number | null,
): Promise<UploadResult> {
  const input: Partial<AdminLessonInput> =
    kind === "video" ? { video_key: key } : { slides_key: key };
  if (durationSeconds !== undefined) input.duration_seconds = durationSeconds;

  try {
    await updateAdminLesson(lessonId, input);
  } catch (error) {
    return { error: errorMessage(error) };
  }
  refresh();
  return {};
}
