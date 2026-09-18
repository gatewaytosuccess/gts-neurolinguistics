import type { Metadata } from "next";
import { auth } from "@clerk/nextjs/server";

import { fetchCurrentUser, type CurrentUser } from "@/lib/api";

export const metadata: Metadata = {
  title: "Dashboard",
};

export default async function DashboardPage() {
  const { userId, redirectToSignIn } = await auth();
  if (!userId) return redirectToSignIn();

  let user: CurrentUser | null = null;

  try {
    user = await fetchCurrentUser();
  } catch {
    // An unreachable API should degrade to a page that says so, not a 500.
  }

  return (
    <main className="mx-auto w-full max-w-[1200px] flex-1 px-md py-2xl sm:px-margin">
      {user ? (
        <AccountSummary user={user} />
      ) : (
        <p className="type-body-sm rounded-sm bg-warning-subtle px-sm py-sm text-warning">
          The course API is not responding, so account details are unavailable.
        </p>
      )}
    </main>
  );
}

function AccountSummary({ user }: { user: CurrentUser }) {
  const rows: Array<[string, string]> = [
    ["Email", user.email],
    ["Role", user.role],
    [
      "Member since",
      new Date(user.created_at).toLocaleDateString("en-US", {
        year: "numeric",
        month: "long",
        day: "numeric",
      }),
    ],
    ["Account id", user.id],
  ];

  return (
    <div>
      <p className="type-label-caps text-accent">Your account</p>
      <h1 className="type-headline-md measure mt-md">
        {user.name ? `Welcome, ${user.name}.` : "Welcome."}
      </h1>
      <p className="type-body-lg measure mt-lg text-accent-strong">
        Your account is set up. Courses will appear here once the catalog is
        live.
      </p>

      <dl className="mt-xl max-w-[560px]">
        {rows.map(([label, value]) => (
          <div
            key={label}
            className="flex justify-between gap-md border-t border-rule py-sm"
          >
            <dt className="type-label-md text-accent">{label}</dt>
            <dd className="type-data-md text-meta-text">{value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
