"use server";

import { refresh } from "next/cache";

import {
  ApiError,
  requestAdminThumbnailUpload,
  setAdminCourseThumbnail,
  type FieldErrors,
} from "@/lib/api";

import type { UploadResult, UploadTicket } from "./uploads";

function errorMessage(error: unknown): string {
  if (!(error instanceof ApiError)) {
    return "The course API is not responding, so nothing changed.";
  }
  if (error.status === 400 && typeof error.body === "object" && error.body) {
    return Object.values(error.body as FieldErrors)
      .flat()
      .join(" ");
  }
  if (error.status === 401 || error.status === 403) {
    return "You no longer have access to the admin area.";
  }
  if (error.status === 404) {
    return "This course no longer exists.";
  }
  return "The course API couldn't change the thumbnail. Try again.";
}

export async function requestThumbnailUpload(
  courseId: string,
  contentType: string,
): Promise<UploadTicket> {
  try {
    return { upload: await requestAdminThumbnailUpload(courseId, contentType) };
  } catch (error) {
    return { error: errorMessage(error) };
  }
}

/** A blank `key` removes the thumbnail. */
export async function saveThumbnail(
  courseId: string,
  key: string,
): Promise<UploadResult> {
  try {
    await setAdminCourseThumbnail(courseId, key);
  } catch (error) {
    return { error: errorMessage(error) };
  }
  refresh();
  return {};
}
