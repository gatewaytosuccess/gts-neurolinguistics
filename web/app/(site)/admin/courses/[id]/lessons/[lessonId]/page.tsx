import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { ApiError, fetchAdminLesson, type AdminLesson } from "@/lib/api";

import { requireAdmin } from "../../../../_lib/require-admin";
import { LessonEditorForm } from "../../../_components/lesson-editor-form";
import { updateLesson } from "../../../_lib/lesson-actions";
import {
  requestLessonUpload,
  saveLessonFile,
} from "../../../_lib/lesson-file-actions";
import { lessonEditorValues } from "../../../_lib/lesson-editor";

export const metadata: Metadata = {
  title: "Lesson · Admin",
};

export default async function AdminLessonPage({
  params,
}: PageProps<"/admin/courses/[id]/lessons/[lessonId]">) {
  // Layouts don't re-render on client navigation, and a layout that skips
  // `children` still sends them in the RSC payload.
  if ((await requireAdmin()) !== "admin") return null;

  const { id, lessonId } = await params;

  let lesson: AdminLesson;
  try {
    lesson = await fetchAdminLesson(lessonId);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    return (
      <p className="type-body-sm rounded-sm bg-warning-subtle px-sm py-sm text-warning">
        The course API is not responding, so this lesson is unavailable.
      </p>
    );
  }

  if (lesson.course.id !== id) notFound();

  return (
    <div>
      <nav aria-label="Breadcrumb">
        <ol className="type-label-md flex flex-wrap items-center gap-x-sm gap-y-xs text-meta-text">
          <li>
            <Link
              href="/admin/courses"
              className="text-primary hover:underline"
            >
              Courses
            </Link>
          </li>
          <li className="flex items-center gap-x-sm">
            <span aria-hidden="true">/</span>
            <Link
              href={`/admin/courses/${lesson.course.id}`}
              className="text-primary hover:underline"
            >
              {lesson.course.title}
            </Link>
          </li>
          <li className="flex items-center gap-x-sm">
            <span aria-hidden="true">/</span>
            Module {String(lesson.module.position).padStart(2, "0")} ·{" "}
            {lesson.module.title}
          </li>
        </ol>
      </nav>

      <h1 className="type-headline-md measure mt-md">{lesson.title}</h1>

      <LessonEditorForm
        // Remounts per lesson, so another lesson's saved state never carries over.
        key={lesson.id}
        action={updateLesson.bind(null, lesson.id)}
        initialState={{ values: lessonEditorValues(lesson), errors: {} }}
        files={{
          videoUrl: lesson.video_url,
          slidesUrl: lesson.slides_url,
          requestUpload: requestLessonUpload.bind(null, lesson.id),
          save: saveLessonFile.bind(null, lesson.id),
        }}
      />
    </div>
  );
}
