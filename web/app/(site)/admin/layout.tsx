import type { Metadata } from "next";

import { AdminNav } from "./_components/admin-nav";
import { requireAdmin } from "./_lib/require-admin";

export const metadata: Metadata = {
  robots: { index: false, follow: false },
};

export default async function AdminLayout({ children }: LayoutProps<"/admin">) {
  const access = await requireAdmin();

  if (access !== "admin") {
    return (
      <main className="mx-auto w-full max-w-[1200px] flex-1 px-md py-2xl sm:px-margin">
        <p className="type-body-sm rounded-sm bg-warning-subtle px-sm py-sm text-warning">
          The course API is not responding, so the admin area is unavailable.
        </p>
      </main>
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-[1200px] flex-1 flex-col lg:flex-row">
      <AdminNav />
      <main className="min-w-0 flex-1 px-md py-2xl sm:px-margin">
        {children}
      </main>
    </div>
  );
}
