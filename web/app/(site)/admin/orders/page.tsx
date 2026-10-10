import type { Metadata } from "next";
import Form from "next/form";
import Link from "next/link";

import { AutoSubmitSelect } from "@/components/auto-submit-select";
import {
  ApiError,
  fetchAdminOrders,
  isOrderStatus,
  type AdminOrderSummary,
  type OrderStatus,
  type Paginated,
} from "@/lib/api";
import { formatPrice } from "@/lib/format";

import { ListPagination } from "../_components/list-pagination";
import { formatDate } from "../_lib/format";
import { firstValue, parsePage } from "../_lib/list-params";
import { requireAdmin } from "../_lib/require-admin";
import {
  ORDER_STATUS_LABELS,
  OrderStatusBadge,
} from "./_components/order-status-badge";

export const metadata: Metadata = {
  title: "Orders · Admin",
};

type Filters = {
  q: string;
  status: OrderStatus | undefined;
};

function listHref({ q, status }: Filters, page = 1) {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (status) params.set("status", status);
  if (page > 1) params.set("page", String(page));
  return params.size ? `/admin/orders?${params}` : "/admin/orders";
}

export default async function AdminOrdersPage({
  searchParams,
}: PageProps<"/admin/orders">) {
  // Layouts don't re-render on client navigation, and a layout that skips
  // `children` still sends them in the RSC payload.
  if ((await requireAdmin()) !== "admin") return null;

  const params = await searchParams;
  const requestedStatus = firstValue(params.status);
  const filters: Filters = {
    q: firstValue(params.q).trim(),
    status: isOrderStatus(requestedStatus) ? requestedStatus : undefined,
  };
  const page = parsePage(firstValue(params.page));

  let orders: Paginated<AdminOrderSummary> | "past-last-page" | null;
  try {
    orders = await fetchAdminOrders({ ...filters, page });
  } catch (error) {
    // A stale link can point past the last page once filters match fewer orders.
    orders =
      error instanceof ApiError && error.status === 404 && page > 1
        ? "past-last-page"
        : null;
  }

  const filtered = Boolean(filters.q || filters.status);

  return (
    <div>
      <p className="type-label-caps text-accent">Admin area</p>
      <h1 className="type-headline-md measure mt-md">Orders</h1>

      <ListControls filters={filters} />

      <div className="mt-xl">
        {orders === null ? (
          <p className="type-body-sm rounded-sm bg-warning-subtle px-sm py-sm text-warning">
            The course API is not responding, so the order list is unavailable.
          </p>
        ) : orders === "past-last-page" ? (
          <p className="type-body-md">
            There are no orders on this page.{" "}
            <Link href={listHref(filters)} className="text-primary underline">
              Go to the first page
            </Link>
            .
          </p>
        ) : orders.count === 0 && filtered ? (
          <p className="type-body-md">
            No orders match these filters.{" "}
            <Link href="/admin/orders" className="text-primary underline">
              Show every order
            </Link>
            .
          </p>
        ) : orders.count === 0 ? (
          <p className="type-body-md">There are no orders yet.</p>
        ) : (
          <>
            <p className="type-body-sm text-meta-text">
              {orders.count === 1 ? "1 order" : `${orders.count} orders`}
            </p>
            <OrderTable orders={orders.results} />
            <ListPagination
              page={page}
              hasPrevious={orders.previous !== null}
              hasNext={orders.next !== null}
              pageHref={(target) => listHref(filters, target)}
            />
          </>
        )}
      </div>
    </div>
  );
}

const fieldClassName =
  "type-body-md w-full rounded-sm border border-border-strong bg-paper-raised px-sm py-sm text-accent-strong placeholder:text-meta-text";

function ListControls({ filters }: { filters: Filters }) {
  const { q, status } = filters;

  return (
    // Remounts per URL: uncontrolled fields would keep stale values across client-side back/forward.
    <Form
      key={JSON.stringify([q, status])}
      action="/admin/orders"
      role="search"
      // Stops the browser restoring stale field values on back/forward without JS.
      autoComplete="off"
      className="mt-xl flex flex-col gap-md md:flex-row md:items-end"
    >
      <div className="min-w-0 md:flex-1">
        <label htmlFor="admin-orders-q" className="type-label-md block">
          Search
        </label>
        <input
          id="admin-orders-q"
          type="search"
          name="q"
          defaultValue={q}
          placeholder="Buyer name, email or order id"
          className={`${fieldClassName} mt-xs`}
        />
      </div>

      <div className="md:w-[160px]">
        <label htmlFor="admin-orders-status" className="type-label-md block">
          Status
        </label>
        <AutoSubmitSelect
          id="admin-orders-status"
          name="status"
          defaultValue={status ?? ""}
          className={`${fieldClassName} mt-xs`}
        >
          <option value="">All</option>
          {Object.entries(ORDER_STATUS_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </AutoSubmitSelect>
      </div>

      <button type="submit" className="button-secondary">
        Search
      </button>
    </Form>
  );
}

function OrderTable({ orders }: { orders: AdminOrderSummary[] }) {
  const headerClassName = "type-label-md px-sm py-sm text-accent";

  return (
    <div className="mt-sm overflow-x-auto">
      <table className="w-full min-w-[680px] border-collapse text-left">
        <thead>
          <tr className="border-b border-border-strong">
            <th scope="col" className={headerClassName}>
              Date
            </th>
            <th scope="col" className={headerClassName}>
              Buyer
            </th>
            <th scope="col" className={headerClassName}>
              Courses
            </th>
            <th scope="col" className={`${headerClassName} text-right`}>
              Total
            </th>
            <th scope="col" className={headerClassName}>
              Status
            </th>
          </tr>
        </thead>
        <tbody>
          {orders.map((order) => (
            <tr key={order.id} className="border-b border-rule align-top">
              <td className="type-data-md whitespace-nowrap px-sm py-sm text-meta-text">
                <time dateTime={order.created_at}>
                  {formatDate(order.created_at)}
                </time>
              </td>
              <td className="px-sm py-sm">
                <span className="type-label-lg block break-words text-accent-strong">
                  {order.buyer.name || order.buyer.email}
                </span>
                {order.buyer.name && (
                  <span className="type-caption block break-all text-meta-text">
                    {order.buyer.email}
                  </span>
                )}
              </td>
              <td className="type-body-sm px-sm py-sm">
                <ul>
                  {order.items.map((item, index) => (
                    <li key={index}>{item.title}</li>
                  ))}
                </ul>
              </td>
              <td className="type-data-md px-sm py-sm text-right">
                {formatPrice(order.total_cents)}
              </td>
              <td className="px-sm py-sm">
                <OrderStatusBadge status={order.status} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
