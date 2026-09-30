import type { Metadata } from "next";
import Form from "next/form";
import Link from "next/link";

import { AutoSubmitSelect } from "@/components/auto-submit-select";
import {
  ApiError,
  fetchAdminUsers,
  isAccountStatus,
  isAdminUserSort,
  isUserRole,
  type AccountStatus,
  type AdminUserSort,
  type AdminUserSummary,
  type Paginated,
  type UserRole,
} from "@/lib/api";

import { ListPagination } from "../_components/list-pagination";
import { firstValue, parsePage } from "../_lib/list-params";
import { requireAdmin } from "../_lib/require-admin";
import { STATUS_LABELS, StatusBadge } from "./_components/status-badge";

export const metadata: Metadata = {
  title: "Users · Admin",
};

const ROLE_LABELS: Record<UserRole, string> = {
  learner: "Learner",
  instructor: "Instructor",
  admin: "Admin",
};

const SORT_LABELS: Record<AdminUserSort, string> = {
  newest: "Newest",
  name: "Name",
  email: "Email",
};

type Filters = {
  q: string;
  role: UserRole | undefined;
  status: AccountStatus | undefined;
  sort: AdminUserSort;
};

function listHref({ q, role, status, sort }: Filters, page = 1) {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (role) params.set("role", role);
  if (status) params.set("status", status);
  if (sort !== "newest") params.set("sort", sort);
  if (page > 1) params.set("page", String(page));
  return params.size ? `/admin/users?${params}` : "/admin/users";
}

export default async function AdminUsersPage({
  searchParams,
}: PageProps<"/admin/users">) {
  // Layouts don't re-render on client navigation, and a layout that skips
  // `children` still sends them in the RSC payload.
  if ((await requireAdmin()) !== "admin") return null;

  const params = await searchParams;
  const requestedRole = firstValue(params.role);
  const requestedStatus = firstValue(params.status);
  const requestedSort = firstValue(params.sort);
  const filters: Filters = {
    q: firstValue(params.q).trim(),
    role: isUserRole(requestedRole) ? requestedRole : undefined,
    status: isAccountStatus(requestedStatus) ? requestedStatus : undefined,
    sort: isAdminUserSort(requestedSort) ? requestedSort : "newest",
  };
  const page = parsePage(firstValue(params.page));

  let users: Paginated<AdminUserSummary> | "past-last-page" | null;
  try {
    users = await fetchAdminUsers({ ...filters, page });
  } catch (error) {
    // A stale link can point past the last page once filters match fewer users.
    users =
      error instanceof ApiError && error.status === 404 && page > 1
        ? "past-last-page"
        : null;
  }

  const filtered = Boolean(filters.q || filters.role || filters.status);

  return (
    <div>
      <p className="type-label-caps text-accent">Admin area</p>
      <h1 className="type-headline-md measure mt-md">Users</h1>

      <ListControls filters={filters} />

      <div className="mt-xl">
        {users === null ? (
          <p className="type-body-sm rounded-sm bg-warning-subtle px-sm py-sm text-warning">
            The course API is not responding, so the user list is unavailable.
          </p>
        ) : users === "past-last-page" ? (
          <p className="type-body-md">
            There are no users on this page.{" "}
            <Link href={listHref(filters)} className="text-primary underline">
              Go to the first page
            </Link>
            .
          </p>
        ) : users.count === 0 && filtered ? (
          <p className="type-body-md">
            No users match these filters.{" "}
            <Link href="/admin/users" className="text-primary underline">
              Show every user
            </Link>
            .
          </p>
        ) : users.count === 0 ? (
          <p className="type-body-md">There are no users yet.</p>
        ) : (
          <>
            <p className="type-body-sm text-meta-text">
              {users.count === 1 ? "1 user" : `${users.count} users`}
            </p>
            <UserTable users={users.results} />
            <ListPagination
              page={page}
              hasPrevious={users.previous !== null}
              hasNext={users.next !== null}
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
  const { q, role, status, sort } = filters;

  return (
    // Remounts per URL: uncontrolled fields would keep stale values across client-side back/forward.
    <Form
      key={JSON.stringify([q, role, status, sort])}
      action="/admin/users"
      role="search"
      // Stops the browser restoring stale field values on back/forward without JS.
      autoComplete="off"
      className="mt-xl flex flex-col gap-md md:flex-row md:items-end"
    >
      <div className="min-w-0 md:flex-1">
        <label htmlFor="admin-users-q" className="type-label-md block">
          Search
        </label>
        <input
          id="admin-users-q"
          type="search"
          name="q"
          defaultValue={q}
          placeholder="Name or email"
          className={`${fieldClassName} mt-xs`}
        />
      </div>

      <div className="md:w-[160px]">
        <label htmlFor="admin-users-role" className="type-label-md block">
          Role
        </label>
        <AutoSubmitSelect
          id="admin-users-role"
          name="role"
          defaultValue={role ?? ""}
          className={`${fieldClassName} mt-xs`}
        >
          <option value="">All</option>
          {Object.entries(ROLE_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </AutoSubmitSelect>
      </div>

      <div className="md:w-[160px]">
        <label htmlFor="admin-users-status" className="type-label-md block">
          Status
        </label>
        <AutoSubmitSelect
          id="admin-users-status"
          name="status"
          defaultValue={status ?? ""}
          className={`${fieldClassName} mt-xs`}
        >
          <option value="">All</option>
          {Object.entries(STATUS_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </AutoSubmitSelect>
      </div>

      <div className="md:w-[160px]">
        <label htmlFor="admin-users-sort" className="type-label-md block">
          Sort by
        </label>
        <AutoSubmitSelect
          id="admin-users-sort"
          name="sort"
          defaultValue={sort}
          className={`${fieldClassName} mt-xs`}
        >
          {Object.entries(SORT_LABELS).map(([value, label]) => (
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

const dateFormat = new Intl.DateTimeFormat("en-US", {
  year: "numeric",
  month: "short",
  day: "numeric",
});

function UserTable({ users }: { users: AdminUserSummary[] }) {
  const headerClassName = "type-label-md px-sm py-sm text-accent";
  const numericHeaderClassName = `${headerClassName} text-right`;
  const numericCellClassName =
    "type-data-md px-sm py-sm text-right text-meta-text";

  return (
    <div className="mt-sm overflow-x-auto">
      <table className="w-full min-w-[680px] border-collapse text-left">
        <thead>
          <tr className="border-b border-border-strong">
            <th scope="col" className={headerClassName}>
              User
            </th>
            <th scope="col" className={headerClassName}>
              Role
            </th>
            <th scope="col" className={headerClassName}>
              Status
            </th>
            <th scope="col" className={numericHeaderClassName}>
              Active enrollments
            </th>
            <th scope="col" className={numericHeaderClassName}>
              Joined
            </th>
          </tr>
        </thead>
        <tbody>
          {users.map((user) => (
            <tr key={user.id} className="border-b border-rule align-top">
              <th scope="row" className="px-sm py-sm font-normal">
                <div className="flex items-start gap-sm">
                  <Avatar user={user} />
                  <div className="min-w-0">
                    <Link
                      href={`/admin/users/${user.id}`}
                      className="type-label-lg block break-words text-accent-strong hover:text-primary hover:underline"
                    >
                      {user.name || user.email}
                    </Link>
                    {user.name && (
                      <span className="type-caption block break-all text-meta-text">
                        {user.email}
                      </span>
                    )}
                  </div>
                </div>
              </th>
              <td className="type-body-sm px-sm py-sm">
                {ROLE_LABELS[user.role]}
              </td>
              <td className="px-sm py-sm">
                <StatusBadge status={user.status} />
              </td>
              <td className={numericCellClassName}>
                {user.active_enrollment_count}
              </td>
              <td className={`${numericCellClassName} whitespace-nowrap`}>
                <time dateTime={user.created_at}>
                  {dateFormat.format(new Date(user.created_at))}
                </time>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Avatar({ user }: { user: AdminUserSummary }) {
  const className = "size-[32px] shrink-0 rounded-full bg-paper-dim";

  if (!user.avatar_url) {
    return (
      <span
        aria-hidden
        className={`${className} type-label-md flex items-center justify-center text-accent`}
      >
        {(user.name || user.email).charAt(0).toUpperCase()}
      </span>
    );
  }

  return (
    // Clerk's image host isn't allowlisted for next/image.
    // eslint-disable-next-line @next/next/no-img-element
    <img src={user.avatar_url} alt="" className={`${className} object-cover`} />
  );
}
