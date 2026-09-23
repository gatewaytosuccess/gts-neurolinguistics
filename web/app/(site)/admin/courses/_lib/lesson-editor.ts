import type { AdminLesson } from "@/lib/api";

/** What the lesson editor shows; the duration is split as typed. */
export type LessonEditorValues = {
  title: string;
  body: string;
  isPreview: boolean;
  minutes: string;
  seconds: string;
};

export type LessonEditorState = {
  values: LessonEditorValues;
  errors: Partial<Record<"title" | "body" | "duration" | "form", string[]>>;
  saved?: boolean;
};

export function lessonEditorValues(lesson: AdminLesson): LessonEditorValues {
  const duration = lesson.duration_seconds;
  return {
    title: lesson.title,
    body: lesson.body,
    isPreview: lesson.is_preview,
    minutes: duration === null ? "" : String(Math.floor(duration / 60)),
    seconds: duration === null ? "" : String(duration % 60),
  };
}
