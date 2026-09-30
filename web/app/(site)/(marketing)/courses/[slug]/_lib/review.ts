import type { MyReview } from "@/lib/api";

export const REVIEW_BODY_MAX_LENGTH = 2000;

/** What the review form shows; `rating` is blank until a star is chosen. */
export type ReviewFormValues = { rating: string; body: string };

export type ReviewFormState = {
  values: ReviewFormValues;
  errors: Partial<Record<keyof ReviewFormValues | "form", string[]>>;
};

export type DeleteReviewState = { error?: string };

export function reviewFormState(review: MyReview | null): ReviewFormState {
  return {
    values: {
      rating: review ? String(review.rating) : "",
      body: review?.body ?? "",
    },
    errors: {},
  };
}
