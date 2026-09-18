import type { Metadata } from "next";
import Link from "next/link";

import { requireAdmin } from "./_lib/require-admin";
import { ADMIN_SECTIONS, type AdminSection } from "./_lib/sections";

export const metadata: Metadata = {
  title: "Admin",
};

const PLANNED_METRICS = ["Enrollments", "Revenue", "Completion rates"];

export default async function AdminDashboardPage() {
  // Layouts don't re-render on client navigation, and a layout that skips
  // `children` still sends them in the RSC payload.
  if ((await requireAdmin()) !== "admin") return null;

  return (
    <div>
      <p className="type-label-caps text-accent">Admin area</p>
      <h1 className="type-headline-md measure mt-md">Dashboard</h1>

      <ul className="mt-xl grid gap-gutter md:grid-cols-2">
        {ADMIN_SECTIONS.map((section) => (
          <li key={section.href}>
            <SectionCard section={section} />
          </li>
        ))}
      </ul>

      <section
        aria-labelledby="analytics-heading"
        className="mt-2xl rounded-lg border border-dashed border-rule p-lg"
      >
        <div className="flex flex-wrap items-baseline justify-between gap-sm">
          <h2 id="analytics-heading" className="type-headline-sm">
            Analytics
          </h2>
          <p className="type-label-caps text-meta-text">Not built yet</p>
        </div>
        <p className="type-body-md measure mt-sm">
          This panel will report on the platform once analytics are built:
        </p>
        <ul className="type-body-md mt-sm list-disc pl-lg">
          {PLANNED_METRICS.map((metric) => (
            <li key={metric}>{metric}</li>
          ))}
        </ul>
      </section>
    </div>
  );
}

function SectionCard({ section }: { section: AdminSection }) {
  const body = (
    <>
      <div className="flex flex-wrap items-baseline justify-between gap-sm">
        <h2 className="type-label-lg">{section.label}</h2>
        {!section.available && (
          <p className="type-label-caps text-meta-text">Coming soon</p>
        )}
      </div>
      <p className="type-body-sm mt-sm text-accent">{section.description}</p>
    </>
  );

  if (!section.available) {
    return (
      <div className="h-full rounded-lg bg-paper-raised p-lg opacity-60">
        {body}
      </div>
    );
  }

  return (
    <Link
      href={section.href}
      className="block h-full rounded-lg border border-transparent bg-paper-raised p-lg hover:border-border-strong"
    >
      {body}
    </Link>
  );
}
