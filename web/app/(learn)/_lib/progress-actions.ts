"use server";

import { refresh } from "next/cache";

import { ApiError, saveLessonProgress } from "@/lib/api";

export type MarkCompleteState = { error?: string };

function errorMessage(error: unknown): string {
  if (!(error instanceof ApiError)) {
    return "The course API is not responding, so nothing changed.";
  }
  if (error.status === 401) {
    return "Your session has ended. Sign in again to record your progress.";
  }
  if (error.status === 403) {
    return "Only learners enrolled in this course can record progress.";
  }
  if (error.status === 404) {
    return "This lesson no longer exists.";
  }
  return "The course API couldn't record your progress. Try again.";
}

// No refresh: nothing on screen shows whether a lesson was opened.
export async function recordOpened(lessonId: string): Promise<void> {
  try {
    await saveLessonProgress(lessonId, { opened: true });
  } catch {
    // A missed visit only affects where Continue lands; never interrupt the lesson for it.
  }
}

export async function setLessonCompleted(
  lessonId: string,
  completed: boolean,
): Promise<MarkCompleteState> {
  try {
    await saveLessonProgress(lessonId, { completed });
  } catch (error) {
    return { error: errorMessage(error) };
  }
  // The sidebar checkmarks and the header bar come from the layout's outline.
  refresh();
  return {};
}
