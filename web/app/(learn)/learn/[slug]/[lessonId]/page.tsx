import type { Metadata } from "next";
import { auth } from "@clerk/nextjs/server";
import { notFound, redirect } from "next/navigation";

import { LessonContent } from "@/components/lesson-content";
import {
  ApiError,
  fetchViewerLesson,
  isAccountSuspended,
  lockedLessonCourse,
  type ViewerLesson,
} from "@/lib/api";

import { LessonFooter } from "../../../_components/lesson-footer";
import { LockedPanel } from "../../../_components/locked-panel";

type Loaded =
  | { kind: "lesson"; lesson: ViewerLesson }
  | { kind: "locked" }
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
    return lockedLessonCourse(error)
      ? { kind: "locked" }
      : { kind: "unavailable" };
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

const mainClass = "flex-1 px-md py-xl sm:px-margin";

export default async function LessonViewerPage({
  params,
}: PageProps<"/learn/[slug]/[lessonId]">) {
  const { slug, lessonId } = await params;
  const [{ userId }, loaded] = await Promise.all([
    auth(),
    loadLesson(slug, lessonId),
  ]);

  if (loaded.kind === "unavailable") {
    return (
      <main className={mainClass}>
        <p className="type-body-sm max-w-[960px] rounded-sm bg-dark-warning-subtle px-sm py-sm text-dark-warning">
          The course API is not responding, so this lesson is unavailable.
        </p>
      </main>
    );
  }

  if (loaded.kind === "locked") {
    return (
      <main className={mainClass}>
        <LockedPanel slug={slug} signedIn={userId !== null} />
      </main>
    );
  }

  const { lesson } = loaded;
  return (
    <main className={mainClass}>
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
  );
}
