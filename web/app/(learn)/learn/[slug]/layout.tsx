import { auth } from "@clerk/nextjs/server";
import { notFound, redirect } from "next/navigation";

import {
  ApiError,
  fetchCurrentUser,
  fetchViewerOutline,
  isAccountSuspended,
  type ViewerOutline,
} from "@/lib/api";

import { ViewerShell } from "../../_components/viewer-shell";

/**
 * `null` when the API fails. Throws Next's not-found error on a 404 and
 * redirects a suspended account, so it must be awaited in the render path.
 */
async function loadOutline(slug: string): Promise<ViewerOutline | null> {
  try {
    return await fetchViewerOutline(slug);
  } catch (error) {
    if (isAccountSuspended(error)) redirect("/suspended");
    if (error instanceof ApiError && error.status === 404) notFound();
    return null;
  }
}

// Fails closed: an unreachable API hides the admin link.
async function isAdmin(): Promise<boolean> {
  try {
    return (await fetchCurrentUser())?.role === "admin";
  } catch {
    return false;
  }
}

export default async function CourseViewerLayout({
  params,
  children,
}: LayoutProps<"/learn/[slug]">) {
  const { slug } = await params;
  const [{ userId }, outline, admin] = await Promise.all([
    auth(),
    loadOutline(slug),
    isAdmin(),
  ]);

  return (
    <ViewerShell
      slug={slug}
      outline={outline}
      admin={admin}
      signedIn={userId !== null}
    >
      {children}
    </ViewerShell>
  );
}
