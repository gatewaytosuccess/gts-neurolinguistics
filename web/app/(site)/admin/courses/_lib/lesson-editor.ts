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
  /** The save was refused because the course is published. */
  problems?: string[];
  saved?: boolean;
};

/** Both blank for `null`. */
export function splitDuration(
  duration: number | null,
): Pick<LessonEditorValues, "minutes" | "seconds"> {
  return {
    minutes: duration === null ? "" : String(Math.floor(duration / 60)),
    seconds: duration === null ? "" : String(duration % 60),
  };
}

export function lessonEditorValues(lesson: AdminLesson): LessonEditorValues {
  return {
    title: lesson.title,
    body: lesson.body,
    isPreview: lesson.is_preview,
    ...splitDuration(lesson.duration_seconds),
  };
}
