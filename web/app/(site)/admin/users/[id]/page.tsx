import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import {
  ApiError,
  fetchAdminUser,
  fetchCurrentUser,
  type AdminUserDetail,
  type AdminUserOrder,
  type AdminUserReview,
  type OrderStatus,
} from "@/lib/api";
import { Stars } from "@/components/stars";
import { formatPrice } from "@/lib/format";

import { requireAdmin } from "../../_lib/require-admin";
import { RoleControl } from "../_components/role-control";
import { StatusBadge } from "../_components/status-badge";
import { SuspensionControl } from "../_components/suspension-control";
import { UserAvatar } from "../_components/user-avatar";
import { formatDate } from "../_lib/format";
import { changeUserRole } from "../_lib/role-actions";

export async function generateMetadata({
  params,
}: PageProps<"/admin/users/[id]">): Promise<Metadata> {
  const fallback = { title: "User · Admin" };
  if ((await requireAdmin()) !== "admin") return fallback;

  const { id } = await params;
  try {
    const user = await fetchAdminUser(id);
    return { title: `${user.name || user.email} · Admin` };
  } catch {
    return fallback;
  }
}

export default async function AdminUserPage({
  params,
}: PageProps<"/admin/users/[id]">) {
  // Layouts don't re-render on client navigation, and a layout that skips
  // `children` still sends them in the RSC payload.
  if ((await requireAdmin()) !== "admin") return null;

  const { id } = await params;

  let user: AdminUserDetail;
  let viewerId: string | undefined;
  try {
    user = await fetchAdminUser(id);
    viewerId = (await fetchCurrentUser())?.id;
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    return (
      <div>
        <BackLink />
        <p className="type-body-sm mt-md rounded-sm bg-warning-subtle px-sm py-sm text-warning">
          The course API is not responding, so this user is unavailable.
        </p>
      </div>
    );
  }

  return (
    <div>
      <BackLink />
      <Header user={user} />

      <section aria-labelledby="access-heading" className="mt-2xl">
        <h2 id="access-heading" className="type-headline-sm">
          Access
        </h2>
        <Access user={user} isSelf={user.id === viewerId} />
        <SuspensionControl user={user} isSelf={user.id === viewerId} />
      </section>

      <section aria-labelledby="orders-heading" className="mt-3xl">
        <h2 id="orders-heading" className="type-headline-sm">
          Orders
        </h2>
        {user.orders.length === 0 ? (
          <p className="type-body-md mt-md">No orders.</p>
        ) : (
          <OrderTable orders={user.orders} />
        )}
      </section>

      <section aria-labelledby="reviews-heading" className="mt-3xl">
        <h2 id="reviews-heading" className="type-headline-sm">
          Reviews
        </h2>
        {user.reviews.length === 0 ? (
          <p className="type-body-md mt-md">No reviews.</p>
        ) : (
          <ReviewList reviews={user.reviews} />
        )}
      </section>
    </div>
  );
}

function BackLink() {
  return (
    <Link
      href="/admin/users"
      className="type-label-md text-primary hover:underline"
    >
      <span aria-hidden="true">←</span> All users
    </Link>
  );
}

function Header({ user }: { user: AdminUserDetail }) {
  return (
    <header className="mt-md flex items-start gap-md">
      <UserAvatar user={user} size="lg" />
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-md">
          <h1 className="type-headline-md measure break-words">
            {user.name || user.email}
          </h1>
          <StatusBadge status={user.status} />
        </div>
        {user.name && (
          <p className="type-body-md mt-xs break-all">{user.email}</p>
        )}
        <p className="type-caption mt-xs text-meta-text">
          {user.has_clerk_identity
            ? "Managed in Clerk"
            : "No Clerk identity: this person deleted their login."}
        </p>
        <p className="type-body-sm mt-sm text-meta-text">
          Joined{" "}
          <time dateTime={user.created_at}>{formatDate(user.created_at)}</time>
        </p>
      </div>
    </header>
  );
}

function Access({ user, isSelf }: { user: AdminUserDetail; isSelf: boolean }) {
  return (
    <dl className="mt-md grid gap-x-md gap-y-xs sm:grid-cols-[max-content_1fr] sm:gap-y-md">
      <div className="contents">
        <dt className="type-label-caps text-meta-text">Role</dt>
        <dd>
          <RoleControl
            // Remounts once a change lands, so the select starts from the new role.
            key={user.role}
            userId={user.id}
            name={user.name || user.email}
            role={user.role}
            status={user.status}
            isSelf={isSelf}
            action={changeUserRole.bind(null, user.id, user.role)}
          />
        </dd>
      </div>
      {user.status === "suspended" && (
        <>
          {user.suspended_at && (
            <div className="contents">
              <dt className="type-label-caps text-meta-text">Suspended</dt>
              <dd className="type-body-md">
                <time dateTime={user.suspended_at}>
                  {formatDate(user.suspended_at)}
                </time>
              </dd>
            </div>
          )}
          <div className="contents">
            <dt className="type-label-caps text-meta-text">Reason</dt>
            <dd className="type-body-md measure whitespace-pre-line break-words">
              {user.suspension_reason || "No reason recorded."}
            </dd>
          </div>
        </>
      )}
    </dl>
  );
}

const ORDER_STATUS_LABELS: Record<OrderStatus, string> = {
  pending: "Pending",
  paid: "Paid",
  refunded: "Refunded",
  failed: "Failed",
};

function OrderTable({ orders }: { orders: AdminUserOrder[] }) {
  const headerClassName = "type-label-md px-sm py-sm text-accent";

  return (
    <div className="mt-md overflow-x-auto">
      <table className="w-full min-w-[560px] border-collapse text-left">
        <thead>
          <tr className="border-b border-border-strong">
            <th scope="col" className={headerClassName}>
              Date
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
              <td className="type-body-sm px-sm py-sm">
                {ORDER_STATUS_LABELS[order.status]}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ReviewList({ reviews }: { reviews: AdminUserReview[] }) {
  return (
    <ul className="mt-md">
      {reviews.map((review) => (
        <li key={review.id} className="border-b border-rule py-md">
          <div className="flex flex-wrap items-center gap-x-md gap-y-xs">
            <Link
              href={
                review.course.status === "published"
                  ? `/courses/${review.course.slug}`
                  : `/admin/courses/${review.course.id}`
              }
              className="type-label-lg break-words text-accent-strong hover:text-primary hover:underline"
            >
              {review.course.title}
            </Link>
            <Stars
              rating={review.rating}
              label={`Rated ${review.rating} out of 5`}
            />
            <ReviewStatusMarker hidden={review.status === "hidden"} />
          </div>
          {review.body && (
            <p className="type-body-sm measure mt-xs line-clamp-2 break-words text-meta-text">
              {review.body}
            </p>
          )}
          <p className="type-caption mt-xs text-meta-text">
            <time dateTime={review.created_at}>
              {formatDate(review.created_at)}
            </time>
          </p>
        </li>
      ))}
    </ul>
  );
}

function ReviewStatusMarker({ hidden }: { hidden: boolean }) {
  return (
    <span
      className={`type-label-caps inline-block whitespace-nowrap rounded-full px-sm py-xs ${
        hidden
          ? "bg-warning-subtle text-warning"
          : "bg-success-subtle text-success"
      }`}
    >
      {hidden ? "Hidden" : "Published"}
    </span>
  );
}
