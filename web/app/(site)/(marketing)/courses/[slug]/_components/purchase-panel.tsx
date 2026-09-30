import Link from "next/link";

import type { CourseSummary } from "@/lib/api";
import { formatPrice } from "@/lib/format";

export function PurchasePanel({
  course,
  enrolled,
  isAdmin,
  className = "",
}: {
  course: CourseSummary;
  enrolled: boolean;
  isAdmin: boolean;
  className?: string;
}) {
  return (
    <aside
      aria-label={enrolled ? "Your enrollment" : "Enroll"}
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

      <p className="type-headline-sm">
        {enrolled ? "You’re enrolled" : formatPrice(course.price_cents)}
      </p>

      {/* Disabled until the cart and the lesson viewer exist. */}
      <button
        type="button"
        disabled
        aria-describedby="purchase-note"
        className="button-primary mt-md"
      >
        {enrolled ? "Continue" : "Add to cart"}
      </button>
      <p id="purchase-note" className="type-caption mt-xs text-meta-text">
        {enrolled ? "The lesson viewer opens soon." : "Enrollment opens soon."}
      </p>

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
