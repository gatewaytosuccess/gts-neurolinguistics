import { auth } from "@clerk/nextjs/server";
import { cache } from "react";

// Server-only: the browser never calls Django directly.
const API_BASE_URL = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
    /** The parsed JSON error body, when the API sent one. */
    readonly body?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export type CurrentUser = {
  id: string;
  email: string;
  name: string;
  avatar_url: string;
  role: "learner" | "instructor" | "admin";
  created_at: string;
};

export type Paginated<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

export type CourseSummary = {
  id: string;
  slug: string;
  title: string;
  description: string;
  price_cents: number;
  thumbnail_url: string;
  rating_average: number | null;
  rating_count: number;
};

export type CourseStatus = "draft" | "published";

export type AdminCourseSummary = {
  id: string;
  title: string;
  slug: string;
  status: CourseStatus;
  price_cents: number;
  module_count: number;
  lesson_count: number;
  active_enrollment_count: number;
  updated_at: string;
};

export type AdminCourse = {
  id: string;
  title: string;
  slug: string;
  description: string;
  price_cents: number;
  /** Blank when the course has no thumbnail. */
  thumbnail_key: string;
  /** Blank when the course has no thumbnail. */
  thumbnail_url: string;
  status: CourseStatus;
  created_at: string;
  updated_at: string;
};

export type AdminCourseInput = {
  title: string;
  description: string;
  price_cents: number;
  /** Blank or missing: generated from the title. */
  slug?: string;
};

export type CurriculumLesson = {
  id: string;
  title: string;
  position: number;
  is_empty: boolean;
  is_preview: boolean;
  /** Learners whose progress deleting the lesson would remove. */
  learners_with_progress: number;
};

export type CurriculumModule = {
  id: string;
  title: string;
  position: number;
  /** Learners with progress on any of its lessons, each counted once. */
  learners_with_progress: number;
  lessons: CurriculumLesson[];
};

/** Everything about a lesson apart from its files. */
export type AdminLesson = {
  id: string;
  title: string;
  /** Markdown. */
  body: string;
  is_preview: boolean;
  /** Positive, or `null` when unknown. */
  duration_seconds: number | null;
  position: number;
  is_empty: boolean;
  module: { id: string; title: string; position: number };
  course: { id: string; title: string; status: CourseStatus };
};

export type AdminLessonInput = Pick<
  AdminLesson,
  "title" | "body" | "is_preview" | "duration_seconds"
>;

/**
 * An S3 presigned POST. The browser sends `fields`, then the file last, as
 * multipart form data to `url`; `key` is where the object lands.
 */
export type PresignedUpload = {
  url: string;
  fields: Record<string, string>;
  key: string;
};

/** DRF's 400 body: messages per field, plus `non_field_errors`. */
export type FieldErrors = Record<string, string[]>;

export type Enrollment = {
  id: string;
  course_id: string;
  course_slug: string;
  source: "purchase" | "manual" | "comp";
  enrolled_at: string;
};

// Shared cache: must never carry a token or return per-user data.
async function publicFetch<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    next: { revalidate: 60 },
  });

  if (!response.ok) {
    throw new ApiError(response.status, `GET ${path} failed`);
  }

  return (await response.json()) as T;
}

async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const { getToken } = await auth();
  const token = await getToken();

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      ...init.headers,
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      "Content-Type": "application/json",
    },
    // Per-user data: never served from a shared cache.
    cache: "no-store",
  });

  if (!response.ok) {
    throw new ApiError(
      response.status,
      `${init.method ?? "GET"} ${path} failed`,
      await response.json().catch(() => undefined),
    );
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

/**
 * `null` if nobody is signed in. Throws if the API is unreachable or returns
 * non-2xx; `ApiError` with status 401 for a suspended account. Safe right
 * after sign-up: the API provisions a missing row. Deduplicated per request.
 */
export const fetchCurrentUser = cache(async (): Promise<CurrentUser | null> => {
  const { userId } = await auth();
  if (!userId) return null;

  return apiFetch<CurrentUser>("/api/users/me/");
});

/**
 * The signed-in user's active enrollments, including in draft courses. `null`
 * if nobody is signed in. Throws `ApiError` with status 401 for a suspended
 * account, and on any other failure.
 */
export async function fetchEnrollments(): Promise<Enrollment[] | null> {
  const { userId } = await auth();
  if (!userId) return null;

  return apiFetch<Enrollment[]>("/api/users/me/enrollments/");
}

export const COURSE_SORTS = ["newest", "price_asc", "price_desc"] as const;

export type CourseSort = (typeof COURSE_SORTS)[number];

export function isCourseSort(value: unknown): value is CourseSort {
  return COURSE_SORTS.includes(value as CourseSort);
}

/**
 * Published courses. `q` matches title or description; a blank `q` is no
 * filter. Throws if the API is unreachable or returns non-2xx.
 */
export async function fetchCourses({
  q = "",
  sort = "newest",
}: { q?: string; sort?: CourseSort } = {}): Promise<Paginated<CourseSummary>> {
  const params = new URLSearchParams();
  if (q.trim()) params.set("q", q.trim());
  if (sort !== "newest") params.set("sort", sort);

  const query = params.size ? `?${params}` : "";
  return publicFetch<Paginated<CourseSummary>>(`/api/courses/${query}`);
}

/**
 * A published course. Throws `ApiError` with status 404 for a draft or unknown
 * slug, and on any other failure.
 */
export async function fetchCourse(slug: string): Promise<CourseSummary> {
  return publicFetch<CourseSummary>(
    `/api/courses/${encodeURIComponent(slug)}/`,
  );
}

export const ADMIN_COURSE_SORTS = ["updated", "title", "created"] as const;

export type AdminCourseSort = (typeof ADMIN_COURSE_SORTS)[number];

export function isAdminCourseSort(value: unknown): value is AdminCourseSort {
  return ADMIN_COURSE_SORTS.includes(value as AdminCourseSort);
}

export function isCourseStatus(value: unknown): value is CourseStatus {
  return value === "draft" || value === "published";
}

/**
 * Every course, drafts included, 20 per page. `q` matches title or slug; a
 * blank `q` is no filter, and a missing `status` means both. Throws `ApiError`
 * with status 404 for a page past the last, 403 for anyone but an admin, and
 * on any other failure.
 */
export async function fetchAdminCourses({
  q = "",
  status,
  sort = "updated",
  page = 1,
}: {
  q?: string;
  status?: CourseStatus;
  sort?: AdminCourseSort;
  page?: number;
} = {}): Promise<Paginated<AdminCourseSummary>> {
  const params = new URLSearchParams();
  if (q.trim()) params.set("q", q.trim());
  if (status) params.set("status", status);
  if (sort !== "updated") params.set("sort", sort);
  if (page > 1) params.set("page", String(page));

  const query = params.size ? `?${params}` : "";
  return apiFetch<Paginated<AdminCourseSummary>>(`/api/admin/courses/${query}`);
}

/**
 * Any course, drafts included. Throws `ApiError` with status 404 for an
 * unknown or malformed id, 403 for anyone but an admin, and on any other
 * failure.
 */
export async function fetchAdminCourse(id: string): Promise<AdminCourse> {
  return apiFetch<AdminCourse>(`/api/admin/courses/${encodeURIComponent(id)}/`);
}

/**
 * Always creates a draft. Throws `ApiError` with status 400 and a
 * `FieldErrors` body for invalid input, 403 for anyone but an admin, and on
 * any other failure.
 */
export async function createAdminCourse(
  input: AdminCourseInput,
): Promise<AdminCourse> {
  return apiFetch<AdminCourse>("/api/admin/courses/", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

/**
 * Only the fields given change. Throws `ApiError` with status 400 and a
 * `FieldErrors` body for invalid input (including a new slug on a published
 * course), 404 for an unknown id, 403 for anyone but an admin, and on any
 * other failure.
 */
export async function updateAdminCourse(
  id: string,
  input: Partial<AdminCourseInput>,
): Promise<AdminCourse> {
  return apiFetch<AdminCourse>(
    `/api/admin/courses/${encodeURIComponent(id)}/`,
    {
      method: "PATCH",
      body: JSON.stringify(input),
    },
  );
}

/**
 * A presigned POST for a new thumbnail. The course is unchanged until
 * `setAdminCourseThumbnail` saves the key. Throws `ApiError` with status 400
 * and a `FieldErrors` body for a type other than JPEG, PNG or WebP, 404 for an
 * unknown id, 403 for anyone but an admin, and on any other failure.
 */
export async function requestAdminThumbnailUpload(
  courseId: string,
  contentType: string,
): Promise<PresignedUpload> {
  return apiFetch<PresignedUpload>(
    `/api/admin/courses/${encodeURIComponent(courseId)}/thumbnail/upload/`,
    { method: "POST", body: JSON.stringify({ content_type: contentType }) },
  );
}

/**
 * A blank `key` removes the thumbnail. The replaced object is deleted from
 * storage. Throws `ApiError` with status 400 and a `FieldErrors` body for a
 * key that isn't an upload for this course, an upload that never finished,
 * or removing a published course's thumbnail; 404 for an unknown id, 403 for
 * anyone but an admin, and on any other failure.
 */
export async function setAdminCourseThumbnail(
  courseId: string,
  key: string,
): Promise<AdminCourse> {
  return apiFetch<AdminCourse>(
    `/api/admin/courses/${encodeURIComponent(courseId)}/`,
    { method: "PATCH", body: JSON.stringify({ thumbnail_key: key }) },
  );
}

/**
 * A course's modules in order, each with its lessons in order. Throws
 * `ApiError` with status 404 for an unknown course, 403 for anyone but an
 * admin, and on any other failure.
 */
export async function fetchAdminCurriculum(
  courseId: string,
): Promise<CurriculumModule[]> {
  return apiFetch<CurriculumModule[]>(
    `/api/admin/courses/${encodeURIComponent(courseId)}/curriculum/`,
  );
}

/*
 * The curriculum edits below throw `ApiError` with status 400 and a
 * `FieldErrors` body for invalid input, 404 for an unknown id, 403 for anyone
 * but an admin, and on any other failure. Positions count from 1, and one out
 * of range is clamped.
 */

/** Appends the module. */
export async function createAdminModule(
  courseId: string,
  title: string,
): Promise<void> {
  await apiFetch(
    `/api/admin/courses/${encodeURIComponent(courseId)}/modules/`,
    { method: "POST", body: JSON.stringify({ title }) },
  );
}

export async function renameAdminModule(
  moduleId: string,
  title: string,
): Promise<void> {
  await apiFetch(`/api/admin/modules/${encodeURIComponent(moduleId)}/`, {
    method: "PATCH",
    body: JSON.stringify({ title }),
  });
}

/** Also deletes its lessons and learners' progress on them. */
export async function deleteAdminModule(moduleId: string): Promise<void> {
  await apiFetch(`/api/admin/modules/${encodeURIComponent(moduleId)}/`, {
    method: "DELETE",
  });
}

export async function moveAdminModule(
  moduleId: string,
  position: number,
): Promise<void> {
  await apiFetch(`/api/admin/modules/${encodeURIComponent(moduleId)}/move/`, {
    method: "POST",
    body: JSON.stringify({ position }),
  });
}

/** Appends an empty lesson. */
export async function createAdminLesson(
  moduleId: string,
  title: string,
): Promise<void> {
  await apiFetch(
    `/api/admin/modules/${encodeURIComponent(moduleId)}/lessons/`,
    { method: "POST", body: JSON.stringify({ title }) },
  );
}

/** Also deletes learners' progress on it. */
export async function deleteAdminLesson(lessonId: string): Promise<void> {
  await apiFetch(`/api/admin/lessons/${encodeURIComponent(lessonId)}/`, {
    method: "DELETE",
  });
}

/**
 * `moduleId` must be a module of the same course, or the API returns 400. A
 * missing `position` with a `moduleId` means last in that module.
 */
export async function moveAdminLesson(
  lessonId: string,
  move:
    | { position: number; moduleId?: string }
    | { position?: number; moduleId: string },
): Promise<void> {
  await apiFetch(`/api/admin/lessons/${encodeURIComponent(lessonId)}/move/`, {
    method: "POST",
    body: JSON.stringify({
      position: move.position,
      module_id: move.moduleId,
    }),
  });
}

/**
 * Throws `ApiError` with status 404 for an unknown or malformed id, 403 for
 * anyone but an admin, and on any other failure.
 */
export async function fetchAdminLesson(id: string): Promise<AdminLesson> {
  return apiFetch<AdminLesson>(`/api/admin/lessons/${encodeURIComponent(id)}/`);
}

/**
 * Only the fields given change. Throws `ApiError` with status 400 and a
 * `FieldErrors` body for invalid input, 404 for an unknown id, 403 for anyone
 * but an admin, and on any other failure.
 */
export async function updateAdminLesson(
  id: string,
  input: Partial<AdminLessonInput>,
): Promise<AdminLesson> {
  return apiFetch<AdminLesson>(
    `/api/admin/lessons/${encodeURIComponent(id)}/`,
    {
      method: "PATCH",
      body: JSON.stringify(input),
    },
  );
}
