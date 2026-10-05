import type { Metadata } from "next";
import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import {
  ApiError,
  fetchViewerContinue,
  fetchViewerOutline,
  isAccountSuspended,
  type ViewerContinue,
} from "@/lib/api";

/**
 * `null` when the API fails. Throws Next's not-found error on a 404 and
 * redirects a suspended account, so it must be awaited in the render path.
 */
async function loadContinue(slug: string): Promise<ViewerContinue | null> {
  try {
    return await fetchViewerContinue(slug);
  } catch (error) {
    if (isAccountSuspended(error)) redirect("/suspended");
    if (error instanceof ApiError && error.status === 404) notFound();
    return null;
  }
}

export async function generateMetadata({
  params,
}: PageProps<"/learn/[slug]">): Promise<Metadata> {
  const { slug } = await params;
  try {
    return { title: (await fetchViewerOutline(slug)).course.title };
  } catch {
    return { title: "Lessons" };
  }
}

const mainClass = "flex-1 px-md py-xl sm:px-margin";

export default async function ContinuePage({
  params,
}: PageProps<"/learn/[slug]">) {
  const { slug } = await params;
  const destination = await loadContinue(slug);

  if (destination === null) {
    return (
      <main className={mainClass}>
        <p className="type-body-sm max-w-[960px] rounded-sm bg-dark-warning-subtle px-sm py-sm text-dark-warning">
          The course API is not responding, so this course is unavailable.
        </p>
      </main>
    );
  }

  if (destination.lesson_id !== null) {
    redirect(
      `/learn/${encodeURIComponent(slug)}/${encodeURIComponent(destination.lesson_id)}`,
    );
  }

  // Published courses always have lessons, so a visitor here just has no preview to open.
  if (destination.access === "visitor") {
    redirect(`/courses/${encodeURIComponent(slug)}`);
  }

  return (
    <main className={mainClass}>
      <section className="card-dark measure">
        <h1 className="type-headline-sm">No lessons yet</h1>
        <p className="type-body-md mt-md text-dark-on-surface-meta">
          This course doesn&rsquo;t have any lessons to open. Check back once
          they&rsquo;ve been added.
        </p>
        <div className="mt-lg flex flex-wrap gap-md">
          <Link href="/dashboard" className="button-primary-dark">
            Go to your dashboard
          </Link>
        </div>
      </section>
    </main>
  );
}
