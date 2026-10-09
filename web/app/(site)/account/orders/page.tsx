import type { Metadata } from "next";
import { auth } from "@clerk/nextjs/server";
import Link from "next/link";
import { redirect } from "next/navigation";

import {
  fetchOrders,
  isAccountSuspended,
  type PurchasedOrder,
} from "@/lib/api";
import { formatDate, formatPrice } from "@/lib/format";

import { OrderStatusBadge } from "./_components/order-status-badge";

export const metadata: Metadata = {
  title: "Order history",
};

/** `null` when the API can't answer. */
async function loadOrders(): Promise<PurchasedOrder[] | null> {
  try {
    return await fetchOrders();
  } catch (error) {
    if (isAccountSuspended(error)) redirect("/suspended");
    return null;
  }
}

export default async function OrderHistoryPage() {
  const { userId, redirectToSignIn } = await auth();
  if (!userId) return redirectToSignIn();

  const orders = await loadOrders();

  return (
    <main className="mx-auto w-full max-w-[1200px] flex-1 px-md py-2xl sm:px-margin">
      <p className="type-label-caps text-accent">Your account</p>
      <h1 className="type-headline-md measure mt-md">Order history</h1>

      {orders === null ? (
        <p className="type-body-sm mt-xl rounded-sm bg-warning-subtle px-sm py-sm text-warning">
          The order API is not responding, so your orders are unavailable.
        </p>
      ) : orders.length === 0 ? (
        <EmptyState />
      ) : (
        <OrderList orders={orders} />
      )}
    </main>
  );
}

function OrderList({ orders }: { orders: PurchasedOrder[] }) {
  return (
    <ul className="mt-xl border-b border-rule">
      {orders.map((order) => {
        const date = formatDate(order.created_at);
        return (
          <li
            key={order.id}
            className="flex flex-col gap-sm border-t border-rule py-md sm:flex-row sm:items-center sm:gap-lg"
          >
            <div className="min-w-0 flex-1">
              <time
                dateTime={order.created_at}
                className="type-caption text-meta-text"
              >
                {date}
              </time>
              <ul className="mt-xs">
                {order.items.map((item) => (
                  <li
                    key={item.course_slug}
                    className="type-label-lg break-words"
                  >
                    {item.course_title}
                  </li>
                ))}
              </ul>
            </div>
            <div className="flex items-center gap-md">
              <OrderStatusBadge status={order.status} />
              <span className="type-data-md tabular-nums">
                {formatPrice(order.total_cents)}
              </span>
            </div>
            <Link
              href={`/account/orders/${encodeURIComponent(order.id)}`}
              className="type-label-md shrink-0 text-tertiary-strong hover:underline"
            >
              Receipt
              <span className="sr-only"> for the order of {date}</span>{" "}
              <span aria-hidden>→</span>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}

function EmptyState() {
  return (
    <div className="measure mt-xl">
      <p className="type-body-lg text-accent-strong">
        You haven&rsquo;t bought a course yet.
      </p>
      <Link href="/courses" className="button-primary mt-lg inline-block">
        Browse courses
      </Link>
    </div>
  );
}
