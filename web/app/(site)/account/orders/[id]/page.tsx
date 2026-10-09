import type { Metadata } from "next";
import { auth } from "@clerk/nextjs/server";
import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import {
  ApiError,
  fetchOrder,
  isAccountSuspended,
  type OrderReceipt,
} from "@/lib/api";
import { formatDate, formatPrice } from "@/lib/format";

import { OrderStatusBadge } from "../_components/order-status-badge";

export const metadata: Metadata = {
  title: "Receipt",
};

/**
 * `null` when the API can't answer. Throws Next's not-found error on a 404,
 * so it must be awaited in the render path.
 */
async function loadOrder(id: string): Promise<OrderReceipt | null> {
  try {
    return await fetchOrder(id);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    if (isAccountSuspended(error)) redirect("/suspended");
    return null;
  }
}

export default async function ReceiptPage({
  params,
}: PageProps<"/account/orders/[id]">) {
  const { userId, redirectToSignIn } = await auth();
  if (!userId) return redirectToSignIn();

  const { id } = await params;
  const order = await loadOrder(id);

  return (
    <main className="mx-auto w-full max-w-[1200px] flex-1 px-md py-2xl sm:px-margin">
      <Link
        href="/account/orders"
        className="type-label-md text-primary hover:underline"
      >
        <span aria-hidden="true">←</span> Order history
      </Link>

      {order === null ? (
        <p className="type-body-sm mt-xl rounded-sm bg-warning-subtle px-sm py-sm text-warning">
          The order API is not responding, so this order is unavailable.
        </p>
      ) : (
        <Receipt order={order} />
      )}
    </main>
  );
}

function Receipt({ order }: { order: OrderReceipt }) {
  return (
    <>
      <p className="type-label-caps mt-xl text-accent">Receipt</p>
      <div className="mt-md flex flex-wrap items-center gap-x-md gap-y-sm">
        <h1 className="type-headline-md">
          Order of{" "}
          <time dateTime={order.created_at}>
            {formatDate(order.created_at)}
          </time>
        </h1>
        <OrderStatusBadge status={order.status} />
      </div>
      {order.status === "refunded" && (
        <p className="type-body-lg measure mt-lg text-accent-strong">
          This order was refunded. You keep access to the course.
        </p>
      )}

      <section aria-label="Order summary" className="measure mt-xl">
        <ul>
          {order.items.map((item) => (
            <li
              key={item.course_slug}
              className="flex items-baseline justify-between gap-md border-t border-rule py-sm"
            >
              <Link
                href={`/courses/${encodeURIComponent(item.course_slug)}`}
                className="type-label-lg min-w-0 break-words text-accent-strong hover:text-primary hover:underline"
              >
                {item.course_title}
              </Link>
              <span className="type-data-md tabular-nums">
                {formatPrice(item.unit_price_cents)}
              </span>
            </li>
          ))}
        </ul>

        <dl className="border-t border-border-strong pt-sm">
          {order.discount_cents > 0 && (
            <>
              <SummaryRow label="Subtotal">
                {formatPrice(order.subtotal_cents)}
              </SummaryRow>
              <SummaryRow label="Discount">
                &minus;{formatPrice(order.discount_cents)}
              </SummaryRow>
            </>
          )}
          <SummaryRow label="Total" emphasis>
            {formatPrice(order.total_cents)}
          </SummaryRow>
        </dl>
      </section>

      {order.receipt_url ? (
        <a
          href={order.receipt_url}
          target="_blank"
          rel="noopener noreferrer"
          className="button-primary mt-xl inline-flex"
        >
          View Stripe receipt
          <span className="sr-only"> (opens in a new tab)</span>
        </a>
      ) : (
        <p className="type-body-md measure mt-xl text-meta-text">
          Stripe&rsquo;s receipt isn&rsquo;t available for this order. It was
          also sent to your email when you paid.
        </p>
      )}
    </>
  );
}

function SummaryRow({
  label,
  emphasis = false,
  children,
}: {
  label: string;
  emphasis?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-baseline justify-between gap-md py-xs">
      <dt
        className={emphasis ? "type-label-lg" : "type-label-md text-meta-text"}
      >
        {label}
      </dt>
      <dd
        className={`tabular-nums ${emphasis ? "type-label-lg" : "type-data-md"}`}
      >
        {children}
      </dd>
    </div>
  );
}
