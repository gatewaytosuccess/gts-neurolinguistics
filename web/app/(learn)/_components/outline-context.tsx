"use client";

import { createContext, useContext } from "react";

import type { ViewerOutline } from "@/lib/api";

export const OutlineContext = createContext<ViewerOutline | null>(null);

/** The layout's outline of the course; `null` when the API couldn't say. */
export function useOutline(): ViewerOutline | null {
  return useContext(OutlineContext);
}

/** `false` when the outline is missing or the caller isn't enrolled. */
export function isLessonCompleted(
  outline: ViewerOutline | null,
  lessonId: string,
): boolean {
  return (
    outline?.modules
      .flatMap((module) => module.lessons)
      .some((lesson) => lesson.id === lessonId && lesson.completed) ?? false
  );
}
