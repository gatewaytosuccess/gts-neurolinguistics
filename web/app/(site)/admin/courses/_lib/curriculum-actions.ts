"use server";

import { refresh } from "next/cache";

import {
  ApiError,
  createAdminLesson,
  createAdminModule,
  deleteAdminLesson,
  deleteAdminModule,
  moveAdminLesson,
  moveAdminModule,
  publishProblems,
  renameAdminModule,
  type FieldErrors,
} from "@/lib/api";

import type { OutlineActionState } from "./curriculum";

function errorMessage(error: unknown): string {
  if (!(error instanceof ApiError)) {
    return "The course API is not responding, so nothing changed.";
  }
  if (error.status === 400 && typeof error.body === "object" && error.body) {
    return Object.values(error.body as FieldErrors)
      .flat()
      .join(" ");
  }
  if (error.status === 401 || error.status === 403) {
    return "You no longer have access to the admin area.";
  }
  if (error.status === 404) {
    return "This was already deleted. Reload the page to see the current curriculum.";
  }
  return "The course API couldn't make this change. Try again.";
}

async function edit(change: () => Promise<void>): Promise<OutlineActionState> {
  try {
    await change();
  } catch (error) {
    const problems = publishProblems(error);
    return problems ? { problems } : { error: errorMessage(error) };
  }
  refresh();
  return {};
}

function title(formData: FormData): string {
  return String(formData.get("title") ?? "").trim();
}

/** `null` unless the form sent a whole number. */
function position(formData: FormData): number | null {
  const value = Number(formData.get("position"));
  return formData.has("position") && Number.isInteger(value) ? value : null;
}

export async function addModule(
  courseId: string,
  _previous: OutlineActionState,
  formData: FormData,
): Promise<OutlineActionState> {
  return edit(() => createAdminModule(courseId, title(formData)));
}

export async function renameModule(
  moduleId: string,
  _previous: OutlineActionState,
  formData: FormData,
): Promise<OutlineActionState> {
  return edit(() => renameAdminModule(moduleId, title(formData)));
}

export async function moveModule(
  moduleId: string,
  _previous: OutlineActionState,
  formData: FormData,
): Promise<OutlineActionState> {
  const to = position(formData);
  if (to === null) return {};
  return edit(() => moveAdminModule(moduleId, to));
}

export async function deleteModule(
  moduleId: string,
): Promise<OutlineActionState> {
  return edit(() => deleteAdminModule(moduleId));
}

export async function addLesson(
  moduleId: string,
  _previous: OutlineActionState,
  formData: FormData,
): Promise<OutlineActionState> {
  return edit(() => createAdminLesson(moduleId, title(formData)));
}

export async function moveLesson(
  lessonId: string,
  _previous: OutlineActionState,
  formData: FormData,
): Promise<OutlineActionState> {
  const to = position(formData);
  if (to === null) return {};
  return edit(() => moveAdminLesson(lessonId, { position: to }));
}

export async function moveLessonToModule(
  lessonId: string,
  _previous: OutlineActionState,
  formData: FormData,
): Promise<OutlineActionState> {
  const moduleId = String(formData.get("module_id") ?? "");
  if (!moduleId) return { error: "Choose a module to move the lesson to." };
  return edit(() => moveAdminLesson(lessonId, { moduleId }));
}

export async function deleteLesson(
  lessonId: string,
): Promise<OutlineActionState> {
  return edit(() => deleteAdminLesson(lessonId));
}
