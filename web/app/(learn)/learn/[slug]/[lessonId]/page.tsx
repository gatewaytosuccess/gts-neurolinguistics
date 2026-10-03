import type { Metadata } from "next";
import { auth } from "@clerk/nextjs/server";
import { notFound, redirect } from "next/navigation";

import { LessonContent } from "@/components/lesson-content";
import {
  ApiError,
  fetchCurrentUser,
  fetchViewerLesson,
  isAccountSuspended,
  lockedLessonCourse,
  type ViewerCourse,
  type ViewerLesson,
} from "@/lib/api";

import { LessonFooter } from "../../../_components/lesson-footer";
import { LockedPanel } from "../../../_components/locked-panel";
import { ViewerHeader } from "../../../_components/viewer-header";

type Loaded =
  | { kind: "lesson"; lesson: ViewerLesson }
  | { kind: "locked"; course: ViewerCourse }
  | { kind: "unavailable" };

/**
 * Throws Next's not-found error on a 404 and redirects a suspended account, so
 * it must be awaited in the render path.
 */
async function loadLesson(slug: string, lessonId: string): Promise<Loaded> {
  try {
    return { kind: "lesson", lesson: await fetchViewerLesson(slug, lessonId) };
  } catch (error) {
    if (isAccountSuspended(error)) redirect("/suspended");
    if (error instanceof ApiError && error.status === 404) notFound();
    const course = lockedLessonCourse(error);
    return course ? { kind: "locked", course } : { kind: "unavailable" };
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

function twoDigits(n: number) {
  return String(n).padStart(2, "0");
}

export async function generateMetadata({
  params,
}: PageProps<"/learn/[slug]/[lessonId]">): Promise<Metadata> {
  const { slug, lessonId } = await params;
  try {
    const lesson = await fetchViewerLesson(slug, lessonId);
    return { title: `${lesson.title} · ${lesson.course.title}` };
  } catch (error) {
    return { title: lockedLessonCourse(error)?.title ?? "Lesson" };
  }
}

export default async function LessonViewerPage({
  params,
}: PageProps<"/learn/[slug]/[lessonId]">) {
  const { slug, lessonId } = await params;
  const [{ userId }, loaded, admin] = await Promise.all([
    auth(),
    loadLesson(slug, lessonId),
    isAdmin(),
  ]);
  const signedIn = userId !== null;

  if (loaded.kind === "unavailable") {
    return (
      <>
        <ViewerHeader slug={slug} viewingAsAdmin={false} signedIn={signedIn} />
        <main className="mx-auto w-full max-w-[1200px] flex-1 px-md py-xl sm:px-margin">
          <p className="type-body-sm rounded-sm bg-dark-warning-subtle px-sm py-sm text-dark-warning">
            The course API is not responding, so this lesson is unavailable.
          </p>
        </main>
      </>
    );
  }

  if (loaded.kind === "locked") {
    return (
      <>
        <ViewerHeader
          slug={slug}
          courseTitle={loaded.course.title}
          viewingAsAdmin={false}
          signedIn={signedIn}
        />
        <main className="mx-auto w-full max-w-[1200px] flex-1 px-md py-xl sm:px-margin">
          <LockedPanel slug={slug} signedIn={signedIn} />
        </main>
      </>
    );
  }

  const { lesson } = loaded;
  return (
    <>
      <ViewerHeader
        slug={slug}
        courseTitle={lesson.course.title}
        editHref={
          admin
            ? `/admin/courses/${lesson.course.id}/lessons/${lesson.id}`
            : undefined
        }
        viewingAsAdmin={lesson.access === "admin"}
        signedIn={signedIn}
      />
      <main className="mx-auto w-full max-w-[1200px] flex-1 px-md py-xl sm:px-margin">
        <div className="max-w-[960px]">
          <p className="type-label-caps text-dark-on-surface-meta">
            Module {twoDigits(lesson.module.position)} &middot;{" "}
            {lesson.module.title}
          </p>
          <h1 className="type-headline-sm mt-sm mb-xl break-words">
            {lesson.title}
          </h1>
          <LessonContent lesson={lesson} tone="dark" />
          <LessonFooter
            slug={slug}
            previousLessonId={lesson.previous_lesson_id}
            nextLessonId={lesson.next_lesson_id}
          />
        </div>
      </main>
    </>
  );
}
