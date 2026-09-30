"use server";

import { refresh, updateTag } from "next/cache";

import {
  ApiError,
  CATALOG_CACHE_TAG,
  courseCacheTag,
  deleteMyReview,
  saveMyReview,
  type FieldErrors,
} from "@/lib/api";

import type { DeleteReviewState, ReviewFormState } from "./review";

function errorMessage(error: unknown, verb: "save" | "delete"): string {
  if (!(error instanceof ApiError)) {
    return `The course API is not responding, so your review wasn't ${verb}d.`;
  }
  if (error.status === 401) {
    return `Your session has ended. Sign in again to ${verb} your review.`;
  }
  if (error.status === 403) {
    return "Only learners enrolled in this course can review it.";
  }
  if (error.status === 404) {
    return "This course is no longer in the catalog.";
  }
  return `The course API couldn't ${verb} your review. Try again.`;
}

function formErrors(error: unknown): ReviewFormState["errors"] {
  if (
    error instanceof ApiError &&
    error.status === 400 &&
    typeof error.body === "object" &&
    error.body
  ) {
    const { rating, body, non_field_errors } = error.body as FieldErrors;
    return { rating, body, form: non_field_errors };
  }
  return { form: [errorMessage(error, "save")] };
}

// The list, the rating summary and the catalog card all read the cached course data.
function expireCourse(slug: string) {
  updateTag(courseCacheTag(slug));
  updateTag(CATALOG_CACHE_TAG);
  refresh();
}

export async function saveReview(
  slug: string,
  _previous: ReviewFormState,
  formData: FormData,
): Promise<ReviewFormState> {
  const values = {
    rating: String(formData.get("rating") ?? ""),
    // Browsers send textarea line breaks as CRLF, which would count twice against the length limit.
    body: String(formData.get("body") ?? "")
      .replaceAll("\r\n", "\n")
      .trim(),
  };

  try {
    // No star chosen sends 0, which the API refuses with its rating message.
    await saveMyReview(slug, {
      rating: Number(values.rating),
      body: values.body,
    });
  } catch (error) {
    return { values, errors: formErrors(error) };
  }

  expireCourse(slug);
  return { values, errors: {} };
}

export async function deleteReview(slug: string): Promise<DeleteReviewState> {
  try {
    await deleteMyReview(slug);
  } catch (error) {
    // Already gone, perhaps from another tab: the page just needs to catch up.
    if (!(error instanceof ApiError && error.status === 404)) {
      return { error: errorMessage(error, "delete") };
    }
  }

  expireCourse(slug);
  return {};
}
