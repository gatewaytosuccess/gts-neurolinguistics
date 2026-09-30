"use client";

import { useActionState } from "react";

import type { MyReview } from "@/lib/api";

import {
  REVIEW_BODY_MAX_LENGTH,
  reviewFormState,
  type DeleteReviewState,
  type ReviewFormState,
} from "../_lib/review";
import { Stars } from "./stars";

type SaveAction = (
  state: ReviewFormState,
  formData: FormData,
) => Promise<ReviewFormState>;

type DeleteAction = (state: DeleteReviewState) => Promise<DeleteReviewState>;

const headingClassName = "type-label-caps text-meta-text";

const fieldClassName =
  "type-body-md mt-xs w-full rounded-sm border bg-paper-raised px-sm py-sm text-accent-strong placeholder:text-meta-text";

const alertClassName =
  "type-body-sm rounded-sm bg-error-subtle px-sm py-sm text-error";

const dangerClassName =
  "type-label-md rounded-sm border border-error bg-paper-raised px-sm py-xs text-error hover:bg-error-subtle disabled:cursor-wait disabled:opacity-60";

const summaryClassName =
  "inline-block cursor-pointer list-none [&::-webkit-details-marker]:hidden";

/**
 * Key it by the review's `updated_at`, so a save or delete remounts it with the
 * disclosures closed and the form reset to the saved review.
 */
export function MyReviewPanel({
  review,
  save,
  remove,
}: {
  review: MyReview | null;
  save: SaveAction;
  remove: DeleteAction;
}) {
  const [state, formAction, pending] = useActionState(
    save,
    reviewFormState(review),
  );

  if (review === null) {
    return (
      <section aria-labelledby="my-review-heading" className="measure">
        <h3 id="my-review-heading" className={headingClassName}>
          Write a review
        </h3>
        <ReviewForm
          state={state}
          action={formAction}
          pending={pending}
          submitLabel="Post review"
        />
      </section>
    );
  }

  const failed = Object.values(state.errors).some(Boolean);

  return (
    <section aria-labelledby="my-review-heading" className="measure">
      <h3 id="my-review-heading" className={headingClassName}>
        Your review
      </h3>
      {review.status === "hidden" && (
        <p className="type-body-sm mt-sm rounded-sm bg-warning-subtle px-sm py-sm text-warning">
          Hidden by a moderator. Only you can see it, and editing it
          doesn&rsquo;t bring it back.
        </p>
      )}
      <div className="mt-sm">
        <Stars
          rating={review.rating}
          label={`Rated ${review.rating} out of 5`}
        />
      </div>
      {review.body && (
        <p className="type-body-md mt-sm break-words whitespace-pre-line">
          {review.body}
        </p>
      )}

      {/* <details> disclosures, so editing and confirming a delete need no JavaScript. */}
      <div className="mt-md flex flex-wrap items-start gap-sm">
        {/* Opens on a refused save, whose errors would otherwise sit out of sight after a no-JS reload. */}
        <details open={failed} className="group open:basis-full">
          <summary
            className={`button-secondary ${summaryClassName} group-open:bg-paper-dim`}
          >
            Edit
          </summary>
          <ReviewForm
            state={state}
            action={formAction}
            pending={pending}
            submitLabel="Save changes"
          />
        </details>
        <DeleteReview remove={remove} />
      </div>
    </section>
  );
}

function DeleteReview({ remove }: { remove: DeleteAction }) {
  const [state, action, pending] = useActionState(remove, {});

  return (
    <details className="group open:basis-full">
      <summary
        className={`${dangerClassName} ${summaryClassName} py-sm group-open:bg-error-subtle`}
      >
        Delete
      </summary>
      <div className="mt-sm flex flex-col gap-sm rounded-sm border border-error bg-paper-raised p-sm">
        <p className="type-body-sm">
          Delete your review? Its rating leaves the course&rsquo;s average, and
          this can&rsquo;t be undone.
        </p>
        <form action={action}>
          <button type="submit" disabled={pending} className={dangerClassName}>
            {pending ? "Deleting…" : "Delete review"}
          </button>
        </form>
        {state.error && (
          <p role="alert" className={alertClassName}>
            {state.error}
          </p>
        )}
      </div>
    </details>
  );
}

function ReviewForm({
  state,
  action,
  pending,
  submitLabel,
}: {
  state: ReviewFormState;
  action: (formData: FormData) => void;
  pending: boolean;
  submitLabel: string;
}) {
  const { values, errors } = state;

  return (
    // Fields read their defaults from `state`: React resets the form after every submission.
    <form action={action} className="mt-md flex flex-col gap-lg">
      {errors.form && (
        <p role="alert" className={alertClassName}>
          {errors.form.join(" ")}
        </p>
      )}
      <StarRating value={values.rating} errors={errors.rating} />
      <div>
        <label htmlFor="review-body" className="type-label-md block">
          Your thoughts (optional)
        </label>
        <textarea
          id="review-body"
          name="body"
          rows={5}
          maxLength={REVIEW_BODY_MAX_LENGTH}
          defaultValue={values.body}
          aria-describedby={
            errors.body
              ? "review-body-hint review-body-error"
              : "review-body-hint"
          }
          aria-invalid={errors.body ? true : undefined}
          className={`${fieldClassName} ${errors.body ? "border-error" : "border-border-strong"}`}
        />
        <p id="review-body-hint" className="type-caption mt-xs text-meta-text">
          Up to 2,000 characters. A rating with no words counts toward the
          average but isn&rsquo;t listed.
        </p>
        {errors.body && (
          <p id="review-body-error" className="type-body-sm mt-xs text-error">
            {errors.body.join(" ")}
          </p>
        )}
      </div>
      <div>
        <button
          type="submit"
          disabled={pending}
          className="button-primary disabled:cursor-wait disabled:opacity-60"
        >
          {pending ? "Saving…" : submitLabel}
        </button>
      </div>
    </form>
  );
}

/**
 * Five native radios, so arrow keys move between them. A star is filled when
 * its own radio or a later one is checked.
 */
function StarRating({ value, errors }: { value: string; errors?: string[] }) {
  return (
    <fieldset aria-describedby={errors ? "review-rating-error" : undefined}>
      <legend className="type-label-md">Rating</legend>
      <div className="mt-xs flex">
        {[1, 2, 3, 4, 5].map((stars) => (
          <label
            key={stars}
            className="cursor-pointer rounded-sm px-[2px] text-[2rem] leading-none text-border-strong has-checked:text-tertiary-strong has-focus-visible:outline-2 has-focus-visible:outline-offset-2 has-focus-visible:outline-primary [&:has(~label_input:checked)]:text-tertiary-strong"
          >
            <input
              type="radio"
              name="rating"
              value={stars}
              required
              defaultChecked={value === String(stars)}
              className="sr-only"
            />
            <span aria-hidden>★</span>
            <span className="sr-only">
              {stars} {stars === 1 ? "star" : "stars"}
            </span>
          </label>
        ))}
      </div>
      {errors && (
        <p id="review-rating-error" className="type-body-sm mt-xs text-error">
          {errors.join(" ")}
        </p>
      )}
    </fieldset>
  );
}
