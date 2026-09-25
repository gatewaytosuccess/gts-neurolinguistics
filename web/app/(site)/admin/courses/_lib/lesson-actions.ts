"use server";

import { refresh } from "next/cache";

import {
  ApiError,
  publishProblems,
  updateAdminLesson,
  type AdminLesson,
  type FieldErrors,
} from "@/lib/api";

import { lessonEditorValues, type LessonEditorState } from "./lesson-editor";

const WHOLE_NUMBER = /^\d+$/;

/**
 * Seconds, `null` for both fields blank, or an error message. A blank field
 * next to a filled one counts as 0. A total of 0 is left for the API to refuse.
 */
function parseDuration(
  minutes: string,
  seconds: string,
): number | null | string {
  if (!minutes && !seconds) return null;
  if (
    (minutes && !WHOLE_NUMBER.test(minutes)) ||
    (seconds && !WHOLE_NUMBER.test(seconds))
  ) {
    return "Enter whole minutes and seconds, such as 12 and 30.";
  }
  const wholeSeconds = Number(seconds || 0);
  if (wholeSeconds > 59) return "Seconds must be between 0 and 59.";
  return Number(minutes || 0) * 60 + wholeSeconds;
}

function formErrors(error: unknown): LessonEditorState["errors"] {
  if (!(error instanceof ApiError)) {
    return {
      form: ["The course API is not responding, so nothing was saved."],
    };
  }
  if (error.status === 400 && typeof error.body === "object" && error.body) {
    const { title, body, duration_seconds, is_preview, non_field_errors } =
      error.body as FieldErrors;
    const form = [...(is_preview ?? []), ...(non_field_errors ?? [])];
    return {
      title,
      body,
      duration: duration_seconds,
      form: form.length ? form : undefined,
    };
  }
  if (error.status === 401 || error.status === 403) {
    return { form: ["You no longer have access to the admin area."] };
  }
  if (error.status === 404) {
    return { form: ["This lesson no longer exists."] };
  }
  return { form: ["The course API couldn't save this lesson. Try again."] };
}

export async function updateLesson(
  id: string,
  _previous: LessonEditorState,
  formData: FormData,
): Promise<LessonEditorState> {
  const field = (name: string) => String(formData.get(name) ?? "");
  const values = {
    title: field("title").trim(),
    body: field("body"),
    isPreview: formData.has("is_preview"),
    minutes: field("minutes").trim(),
    seconds: field("seconds").trim(),
  };

  const duration = parseDuration(values.minutes, values.seconds);
  if (typeof duration === "string") {
    return { values, errors: { duration: [duration] } };
  }

  let lesson: AdminLesson;
  try {
    lesson = await updateAdminLesson(id, {
      title: values.title,
      body: values.body,
      is_preview: values.isPreview,
      duration_seconds: duration,
    });
  } catch (error) {
    const problems = publishProblems(error);
    if (problems) return { values, errors: {}, problems };
    return { values, errors: formErrors(error) };
  }

  // Re-renders the heading and breadcrumb above the form.
  refresh();
  return { values: lessonEditorValues(lesson), errors: {}, saved: true };
}
