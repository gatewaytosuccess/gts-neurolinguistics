import type { Metadata } from "next";
import { auth } from "@clerk/nextjs/server";
import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import {
  ApiError,
  fetchCheckoutOrder,
  isAccountSuspended,
  type CheckoutOrder,
} from "@/lib/api";
import { formatDate, formatPrice } from "@/lib/format";

import { ConfirmingPayment } from "./_components/confirming-payment";

export const metadata: Metadata = {
  title: "Order confirmation",
  robots: { index: false, follow: false },
};

/**
 * `null` while the order can't be loaded for a reason a refresh might fix.
 * Throws Next's not-found error on a 404, so it must be awaited in the render path.
 */
async function loadOrder(sessionId: string): Promise<CheckoutOrder | null> {
  try {
    return await fetchCheckoutOrder(sessionId);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    if (isAccountSuspended(error)) redirect("/suspended");
    return null;
  }
}

export default async function CheckoutSuccessPage({
  searchParams,
}: PageProps<"/checkout/success">) {
  const { userId, redirectToSignIn } = await auth();
  if (!userId) return redirectToSignIn();

  const { session_id: sessionId } = await searchParams;
  if (typeof sessionId !== "string" || !sessionId) notFound();

  const order = await loadOrder(sessionId);

  return (
    <main className="mx-auto w-full max-w-[1200px] flex-1 px-md py-2xl sm:px-margin">
      <p className="type-label-caps text-accent">Your order</p>
      {order === null || order.status === "pending" ? (
        <ConfirmingPayment />
      ) : order.status === "expired" ? (
        <Expired order={order} />
      ) : (
        <Confirmed order={order} />
      )}
    </main>
  );
}

function Confirmed({ order }: { order: CheckoutOrder }) {
  const [first] = order.items;
  const titles = order.items.map((item) => item.course_title).join(", ");

  return (
    <>
      <h1 className="type-headline-md measure mt-md break-words">
        You&rsquo;re enrolled in {titles}.
      </h1>
      {order.status === "refunded" && (
        <p className="type-body-lg measure mt-lg text-accent-strong">
          This order was refunded. You keep access to the course.
        </p>
      )}

      <dl className="measure mt-xl grid grid-cols-[auto_1fr] gap-x-lg gap-y-sm border-t border-rule pt-md">
        <dt className="type-label-md text-meta-text">Paid</dt>
        <dd className="type-body-md tabular-nums">
          {formatPrice(order.total_cents)}
        </dd>
        <dt className="type-label-md text-meta-text">Date</dt>
        <dd className="type-body-md">{formatDate(order.created_at)}</dd>
      </dl>

      {first && (
        <Link
          href={`/learn/${encodeURIComponent(first.course_slug)}`}
          className="button-primary mt-xl inline-flex"
        >
          Start course
        </Link>
      )}
    </>
  );
}

function Expired({ order }: { order: CheckoutOrder }) {
  const [first] = order.items;

  return (
    <>
      <h1 className="type-headline-md measure mt-md">
        This checkout expired before it was paid.
      </h1>
      <p className="type-body-lg measure mt-lg text-accent-strong">
        You haven&rsquo;t been charged. You can start a new checkout from the
        course page.
      </p>
      {first && (
        <Link
          href={`/courses/${encodeURIComponent(first.course_slug)}`}
          className="button-secondary mt-xl inline-flex"
        >
          Back to {first.course_title}
        </Link>
      )}
    </>
  );
}
