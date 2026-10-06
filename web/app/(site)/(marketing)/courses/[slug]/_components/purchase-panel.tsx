import Link from "next/link";

import type { CourseDetail } from "@/lib/api";
import { formatApproximateDuration, formatPrice } from "@/lib/format";

export type EnrollmentState = "enrolled" | "revoked" | "none";

export function PurchasePanel({
  course,
  enrollment,
  isAdmin,
  className = "",
}: {
  course: CourseDetail;
  enrollment: EnrollmentState;
  isAdmin: boolean;
  className?: string;
}) {
  return (
    <aside
      aria-label={enrollment === "none" ? "Enroll" : "Your enrollment"}
      className={`rounded-lg bg-paper-raised p-lg ${className}`}
    >
      {course.thumbnail_url && (
        // CloudFront's domain is a Django setting, so next/image has no host to allowlist.
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={course.thumbnail_url}
          alt=""
          className="mb-lg aspect-video w-full rounded-xs bg-paper-dim object-cover"
        />
      )}

      {enrollment === "enrolled" && (
        <>
          <p className="type-headline-sm">You&rsquo;re enrolled</p>
          <Link
            href={`/learn/${encodeURIComponent(course.slug)}`}
            className="button-primary mt-md"
          >
            Continue
          </Link>
        </>
      )}

      {enrollment === "revoked" && (
        <>
          <p className="type-headline-sm">Your access has ended</p>
          <p className="type-body-sm mt-sm">
            Your progress is saved. If your access is restored, you&rsquo;ll
            pick up where you left off.
          </p>
          <p className="type-body-sm mt-sm">
            Questions?{" "}
            <Link
              href="/contact"
              className="text-primary underline hover:text-primary-strong"
            >
              Contact us
            </Link>
          </p>
        </>
      )}

      {enrollment === "none" && (
        <>
          <p className="type-headline-sm">{formatPrice(course.price_cents)}</p>
          {/* Disabled until the cart exists. */}
          <button
            type="button"
            disabled
            aria-describedby="purchase-note"
            className="button-primary mt-md"
          >
            Add to cart
          </button>
          <p id="purchase-note" className="type-caption mt-xs text-meta-text">
            Enrollment opens soon.
          </p>
        </>
      )}

      <CourseStats course={course} />

      {isAdmin && (
        <p className="mt-lg border-t border-rule pt-md">
          <Link
            href={`/admin/courses/${course.id}`}
            className="type-label-md text-primary underline hover:text-primary-strong"
          >
            Edit in admin &rarr;
          </Link>
        </p>
      )}
    </aside>
  );
}

function CourseStats({ course }: { course: CourseDetail }) {
  const stats: [string, string][] = [
    ["Modules", String(course.module_count)],
    ["Lessons", String(course.lesson_count)],
  ];
  if (course.duration_seconds !== null) {
    stats.push(["Length", formatApproximateDuration(course.duration_seconds)]);
  }
  if (course.preview_lesson_count > 0) {
    stats.push(["Preview lessons", String(course.preview_lesson_count)]);
  }

  return (
    <dl className="mt-lg grid grid-cols-2 gap-x-md gap-y-sm border-t border-rule pt-md">
      {stats.map(([term, value]) => (
        <div key={term}>
          <dt className="type-label-caps text-meta-text">{term}</dt>
          <dd className="type-data-md mt-xs">{value}</dd>
        </div>
      ))}
    </dl>
  );
}
