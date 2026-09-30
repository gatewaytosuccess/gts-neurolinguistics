import Link from "next/link";
import type { ReactNode } from "react";

import type { CourseReview, Paginated } from "@/lib/api";
import { formatMonthYear } from "@/lib/format";

import { Stars } from "./stars";

const REVIEWS_PAGE_SIZE = 10;

function reviewsHref(slug: string, page: number) {
  const query = page > 1 ? `?reviews=${page}` : "";
  return `/courses/${encodeURIComponent(slug)}${query}#reviews`;
}

/**
 * `reviews` is `null` when they couldn't be loaded. `ownReview` is the
 * learner's own review or its form, shown above the list.
 */
export function Reviews({
  slug,
  ratingAverage,
  ratingCount,
  reviews,
  page,
  ownReview,
}: {
  slug: string;
  ratingAverage: number | null;
  ratingCount: number;
  reviews: Paginated<CourseReview> | null;
  page: number;
  ownReview?: ReactNode;
}) {
  return (
    <section id="reviews" aria-labelledby="reviews-heading">
      <div className="mx-auto grid max-w-[1200px] gap-xl px-md py-2xl sm:px-margin md:grid-cols-12 md:gap-gutter lg:py-3xl">
        <div className="md:col-span-4">
          <h2
            id="reviews-heading"
            className="type-headline-sm lg:type-headline-md"
          >
            Reviews
          </h2>
          <RatingSummary average={ratingAverage} count={ratingCount} />
        </div>

        <div className="flex min-w-0 flex-col gap-2xl md:col-span-8 lg:col-span-7 lg:col-start-6">
          {ownReview}
          {reviews === null ? (
            <p className="type-body-sm rounded-sm bg-warning-subtle px-sm py-sm text-warning">
              Reviews are unavailable right now.
            </p>
          ) : (
            reviews.results.length > 0 && (
              <div>
                <ol className="measure">
                  {reviews.results.map((review) => (
                    <ReviewItem key={review.id} review={review} />
                  ))}
                </ol>
                <Pagination
                  slug={slug}
                  page={page}
                  pageCount={Math.ceil(reviews.count / REVIEWS_PAGE_SIZE)}
                  hasPrevious={reviews.previous !== null}
                  hasNext={reviews.next !== null}
                />
              </div>
            )
          )}
        </div>
      </div>
    </section>
  );
}

function RatingSummary({
  average,
  count,
}: {
  average: number | null;
  count: number;
}) {
  if (average === null || count === 0) {
    return <p className="type-body-md mt-md text-meta-text">No ratings yet</p>;
  }

  return (
    <div className="mt-md">
      <p className="flex items-baseline gap-sm">
        <span className="type-headline-md">{average.toFixed(1)}</span>
        <Stars
          rating={Math.round(average)}
          label={`Rated ${average.toFixed(1)} out of 5`}
        />
      </p>
      <p className="type-caption mt-xs text-meta-text">
        from {count.toLocaleString("en-US")}{" "}
        {count === 1 ? "rating" : "ratings"}
      </p>
    </div>
  );
}

function ReviewItem({ review }: { review: CourseReview }) {
  return (
    <li className="border-t border-rule py-lg first:border-t-0 first:pt-0">
      <Stars rating={review.rating} label={`Rated ${review.rating} out of 5`} />
      <p className="type-caption mt-xs text-meta-text">
        {review.author_name || "A learner"} &middot;{" "}
        <time dateTime={review.created_at}>
          {formatMonthYear(review.created_at)}
        </time>
      </p>
      <p className="type-body-md mt-sm break-words whitespace-pre-line">
        {review.body}
      </p>
    </li>
  );
}

function Pagination({
  slug,
  page,
  pageCount,
  hasPrevious,
  hasNext,
}: {
  slug: string;
  page: number;
  pageCount: number;
  hasPrevious: boolean;
  hasNext: boolean;
}) {
  if (!hasPrevious && !hasNext) return null;

  const linkClassName = "type-label-md text-primary underline";
  const disabledClassName = "type-label-md text-meta-text opacity-60";

  return (
    <nav
      aria-label="Reviews pagination"
      className="measure mt-lg flex items-center justify-between gap-md"
    >
      {hasPrevious ? (
        <Link href={reviewsHref(slug, page - 1)} className={linkClassName}>
          Previous
        </Link>
      ) : (
        <span className={disabledClassName}>Previous</span>
      )}
      <span className="type-body-sm text-meta-text">
        Page {page} of {pageCount}
      </span>
      {hasNext ? (
        <Link href={reviewsHref(slug, page + 1)} className={linkClassName}>
          Next
        </Link>
      ) : (
        <span className={disabledClassName}>Next</span>
      )}
    </nav>
  );
}
