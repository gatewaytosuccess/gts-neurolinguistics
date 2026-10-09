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

export type LessonKind = "video" | "slides" | "text";

export type CourseLesson = {
  id: string;
  title: string;
  position: number;
  /** Positive, or `null` when unknown. */
  duration_seconds: number | null;
  is_preview: boolean;
  /** Which kinds of content it has, in the order video, slides, text. */
  kinds: LessonKind[];
};

export type CourseModule = {
  id: string;
  title: string;
  position: number;
  lesson_count: number;
  lessons: CourseLesson[];
};

export type CourseDetail = CourseSummary & {
  module_count: number;
  lesson_count: number;
  preview_lesson_count: number;
  /** The sum of the lessons' known durations; `null` when no lesson has one. */
  duration_seconds: number | null;
  /** In order, each with its lessons in order. */
  modules: CourseModule[];
};

export type CourseReview = {
  id: string;
  /** 1 to 5. */
  rating: number;
  /** Plain text, never blank; line breaks are the author's. */
  body: string;
  /** "Maria G."; blank when the author has no name. */
  author_name: string;
  created_at: string;
  updated_at: string;
};

export type ReviewStatus = "published" | "hidden";

/** The signed-in learner's own review of a course. */
export type MyReview = {
  id: string;
  /** 1 to 5. */
  rating: number;
  /** Plain text; blank for a rating-only review. */
  body: string;
  /** A hidden review is shown to nobody but its author. */
  status: ReviewStatus;
  created_at: string;
  updated_at: string;
};

export type MyReviewInput = { rating: number; body: string };

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

export type AdminLesson = {
  id: string;
  title: string;
  /** Markdown. */
  body: string;
  is_preview: boolean;
  /** Positive, or `null` when unknown. */
  duration_seconds: number | null;
  /** Blank when the lesson has no video. */
  video_key: string;
  /** Presigned, expiring after an hour; blank when the lesson has no video. */
  video_url: string;
  /** Blank when the lesson has no slides. */
  slides_key: string;
  /** Presigned, expiring after an hour; blank when the lesson has no slides. */
  slides_url: string;
  position: number;
  is_empty: boolean;
  module: { id: string; title: string; position: number };
  course: { id: string; title: string; slug: string; status: CourseStatus };
};

export type AdminLessonInput = Pick<
  AdminLesson,
  | "title"
  | "body"
  | "is_preview"
  | "duration_seconds"
  | "video_key"
  | "slides_key"
>;

export type LessonFileKind = "video" | "slides";

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

/**
 * The problems in a 400 refusing to publish a course, or refusing an edit that
 * would leave a published course unpublishable; `null` for any other error.
 */
export function publishProblems(error: unknown): string[] | null {
  if (!(error instanceof ApiError) || error.status !== 400) return null;
  const { problems } = (error.body ?? {}) as { problems?: unknown };
  return Array.isArray(problems) ? problems.map(String) : null;
}

/**
 * Whether the API refused the session because the user is suspended, as
 * opposed to an expired or invalid token. Signed-in-only pages redirect to
 * `/suspended` on it.
 */
export function isAccountSuspended(error: unknown): boolean {
  if (!(error instanceof ApiError) || error.status !== 401) return false;
  const { code } = (error.body ?? {}) as { code?: unknown };
  return code === "account_suspended";
}

export type EnrollmentSource = "purchase" | "manual" | "comp";

export type Enrollment = {
  id: string;
  course_id: string;
  course_slug: string;
  course_title: string;
  /** Blank when the course has no thumbnail. */
  course_thumbnail_url: string;
  source: EnrollmentSource;
  enrolled_at: string;
  /** Over the course's current lessons. */
  lesson_count: number;
  completed_lesson_count: number;
  /** The caller's latest progress update in the course; `null` before they start it. */
  last_activity_at: string | null;
  /** Where `/learn/[slug]` redirects them; `null` when the course has no lessons. */
  continue_lesson_id: string | null;
  continue_lesson_title: string | null;
};

/**
 * What the caller is to a course in the lesson viewer. An enrolled admin is
 * `enrolled`; a revoked learner is a `visitor`.
 */
export type ViewerAccess = "enrolled" | "admin" | "visitor";

export type ViewerCourse = { id: string; title: string; slug: string };

export type ViewerLesson = {
  id: string;
  title: string;
  module: { title: string; position: number };
  course: ViewerCourse;
  /** Markdown; blank when the lesson has no text. */
  body: string;
  /** Presigned, expiring after four hours; blank when the lesson has no video. */
  video_url: string;
  /** Presigned, expiring after four hours; blank when the lesson has no slides. */
  slides_url: string;
  /** In curriculum order across modules; `null` on the first lesson. */
  previous_lesson_id: string | null;
  /** In curriculum order across modules; `null` on the last lesson. */
  next_lesson_id: string | null;
  access: ViewerAccess;
  /** `null` unless the caller is enrolled. */
  progress: ViewerLessonProgress | null;
};

export type ViewerLessonProgress = {
  status: ProgressStatus;
  /** Where the video was last saved; `0` if it never was. */
  last_position_seconds: number;
};

export type OutlineLesson = Pick<
  CourseLesson,
  "id" | "title" | "duration_seconds" | "is_preview" | "kinds"
> & {
  /** Opening it shows the locked panel instead of the content. */
  locked: boolean;
  /** Always `false` unless the caller is enrolled. */
  completed: boolean;
};

export type OutlineModule = {
  id: string;
  title: string;
  position: number;
  lessons: OutlineLesson[];
};

/** A course's whole curriculum as the lesson viewer's sidebar shows it. */
export type ViewerOutline = {
  course: ViewerCourse;
  access: ViewerAccess;
  /** Set only when the caller's own enrollment in the course is revoked. */
  revoked_at: string | null;
  lesson_count: number;
  /** The caller's own completed lessons; `0` unless enrolled. */
  completed_lesson_count: number;
  /** In curriculum order, empty modules included. */
  modules: OutlineModule[];
};

export type ProgressStatus = "not_started" | "in_progress" | "completed";

export type LessonProgressInput = {
  /** Starts the lesson and moves its `updated_at`; never undoes completion. */
  opened?: true;
  /** `false` puts a completed lesson back to `in_progress`. */
  completed?: boolean;
  /** A non-negative whole number; starts the lesson but never undoes completion. */
  position_seconds?: number;
};

export type LessonProgress = {
  lesson_id: string;
  status: ProgressStatus;
  completed_at: string | null;
  last_position_seconds: number;
  lesson_count: number;
  completed_lesson_count: number;
};

/**
 * The course of a 403 refusing a locked lesson; `null` for any other error.
 */
export function lockedLessonCourse(error: unknown): ViewerCourse | null {
  if (!(error instanceof ApiError) || error.status !== 403) return null;
  const { code, course } = (error.body ?? {}) as {
    code?: unknown;
    course?: ViewerCourse;
  };
  return code === "lesson_locked" && course ? course : null;
}

/** Tags every public fetch; expire it when a course enters or leaves the catalog. */
export const CATALOG_CACHE_TAG = "catalog";

/** Tags one course's public data; expire it when an admin edits that course. */
export function courseCacheTag(slug: string) {
  return `course:${slug}`;
}

// Shared cache: must never carry a token or return per-user data.
async function publicFetch<T>(path: string, tags: string[] = []): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    next: { revalidate: 60, tags: [CATALOG_CACHE_TAG, ...tags] },
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
 * non-2xx; a suspended account's `ApiError` passes `isAccountSuspended`. Safe
 * right after sign-up: the API provisions a missing row. Deduplicated per request.
 */
export const fetchCurrentUser = cache(async (): Promise<CurrentUser | null> => {
  const { userId } = await auth();
  if (!userId) return null;

  return apiFetch<CurrentUser>("/api/users/me/");
});

/**
 * The signed-in user's active enrollments, including in draft courses, most
 * recent activity first and then courses not yet started, newest enrollment
 * first. `null` if nobody is signed in. Throws on any failure; a suspended
 * account's `ApiError` passes `isAccountSuspended`.
 */
export async function fetchEnrollments(): Promise<Enrollment[] | null> {
  const { userId } = await auth();
  if (!userId) return null;

  return apiFetch<Enrollment[]>("/api/users/me/enrollments/");
}

/**
 * A lesson as the lesson viewer shows it; signing in is optional. Throws
 * `ApiError` with status 403 for a locked lesson (see `lockedLessonCourse`),
 * 404 for an unknown or malformed id, a lesson of another course, or a draft
 * course the caller can't see, and on any other failure; a suspended
 * account's passes `isAccountSuspended`. Deduplicated per request.
 */
export const fetchViewerLesson = cache(
  async (slug: string, lessonId: string): Promise<ViewerLesson> =>
    apiFetch<ViewerLesson>(
      `/api/learn/${encodeURIComponent(slug)}/lessons/${encodeURIComponent(lessonId)}/`,
    ),
);

/**
 * The lesson viewer's outline of a course; signing in is optional. Throws
 * `ApiError` with status 404 for an unknown course or a draft the caller
 * can't see, and on any other failure; a suspended account's passes
 * `isAccountSuspended`. Deduplicated per request.
 */
export const fetchViewerOutline = cache(
  async (slug: string): Promise<ViewerOutline> =>
    apiFetch<ViewerOutline>(`/api/learn/${encodeURIComponent(slug)}/`),
);

export type ViewerContinue = {
  /**
   * An enrolled learner's Continue lesson, an admin's first lesson or a
   * visitor's first preview lesson; `null` when there's no such lesson.
   */
  lesson_id: string | null;
  access: ViewerAccess;
};

/**
 * Where `/learn/[slug]` sends the caller; signing in is optional. Throws
 * `ApiError` with status 404 for an unknown course or a draft the caller
 * can't see, and on any other failure; a suspended account's passes
 * `isAccountSuspended`.
 */
export async function fetchViewerContinue(
  slug: string,
): Promise<ViewerContinue> {
  return apiFetch<ViewerContinue>(
    `/api/learn/${encodeURIComponent(slug)}/continue/`,
  );
}

/**
 * Records the signed-in learner's progress on a lesson. Throws `ApiError`
 * with status 403 without an active enrollment in its course (admins
 * included), 404 for an unknown lesson, and on any other failure.
 */
export async function saveLessonProgress(
  lessonId: string,
  input: LessonProgressInput,
): Promise<LessonProgress> {
  return apiFetch<LessonProgress>(
    `/api/lessons/${encodeURIComponent(lessonId)}/progress/`,
    { method: "PUT", body: JSON.stringify(input) },
  );
}

/**
 * Starts a Stripe Checkout for one course and returns the Stripe page to send
 * the signed-in user to. Throws `ApiError` with status 409 while they hold an
 * active enrollment in it, 404 for an unknown or draft course, 502 if Stripe
 * refuses, and on any other failure; a suspended account's passes
 * `isAccountSuspended`.
 */
export async function startCheckout(slug: string): Promise<{ url: string }> {
  return apiFetch<{ url: string }>("/api/checkout/", {
    method: "POST",
    body: JSON.stringify({ course: slug }),
  });
}

export type Order = {
  id: string;
  created_at: string;
  status: OrderStatus;
  total_cents: number;
  items: {
    course_slug: string;
    course_title: string;
    unit_price_cents: number;
  }[];
};

/**
 * The order a Stripe Checkout Session paid for, fulfilled first if Stripe
 * reports it paid; still `pending` while it doesn't, or can't be reached.
 * Throws `ApiError` with status 404 unless the session is one of the signed-in
 * user's orders, and on any other failure; a suspended account's passes
 * `isAccountSuspended`.
 */
export async function fetchCheckoutOrder(sessionId: string): Promise<Order> {
  return apiFetch<Order>(
    `/api/checkout/sessions/${encodeURIComponent(sessionId)}/`,
  );
}

/** An order something was bought with. */
export type PurchasedOrder = Order & { status: "paid" | "refunded" };

export type OrderReceipt = PurchasedOrder & {
  subtotal_cents: number;
  discount_cents: number;
  /** Blank when Stripe couldn't be reached at fulfilment. */
  receipt_url: string;
};

/**
 * The signed-in user's paid and refunded orders, newest first. Throws on any
 * failure; a suspended account's `ApiError` passes `isAccountSuspended`.
 */
export async function fetchOrders(): Promise<PurchasedOrder[]> {
  return apiFetch<PurchasedOrder[]>("/api/users/me/orders/");
}

/**
 * One of the signed-in user's paid or refunded orders. Throws `ApiError` with
 * status 404 for a pending or expired order, anyone else's, or a malformed id,
 * and on any other failure; a suspended account's passes `isAccountSuspended`.
 */
export async function fetchOrder(id: string): Promise<OrderReceipt> {
  return apiFetch<OrderReceipt>(
    `/api/users/me/orders/${encodeURIComponent(id)}/`,
  );
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
 * A published course with its curriculum. Throws `ApiError` with status 404
 * for a draft or unknown slug, and on any other failure.
 */
export async function fetchCourse(slug: string): Promise<CourseDetail> {
  return publicFetch<CourseDetail>(
    `/api/courses/${encodeURIComponent(slug)}/`,
    [courseCacheTag(slug)],
  );
}

/**
 * A published course's reviews that have a body, newest first, 10 per page.
 * Rating-only reviews are left out but count in the course's rating. Throws
 * `ApiError` with status 404 for a draft or unknown slug or a page past the
 * last, and on any other failure.
 */
export async function fetchCourseReviews(
  slug: string,
  page = 1,
): Promise<Paginated<CourseReview>> {
  const query = page > 1 ? `?page=${page}` : "";
  return publicFetch<Paginated<CourseReview>>(
    `/api/courses/${encodeURIComponent(slug)}/reviews/${query}`,
    [courseCacheTag(slug)],
  );
}

/**
 * The signed-in learner's review of a published course, hidden or not. `null`
 * if nobody is signed in or they have none. Throws `ApiError` with status 401
 * for a suspended account, and on any other failure.
 */
export async function fetchMyReview(slug: string): Promise<MyReview | null> {
  const { userId } = await auth();
  if (!userId) return null;

  try {
    return await apiFetch<MyReview>(
      `/api/courses/${encodeURIComponent(slug)}/reviews/mine/`,
    );
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}

/**
 * Creates or replaces the learner's review; a hidden review stays hidden.
 * Throws `ApiError` with status 400 and a `FieldErrors` body for invalid
 * input, 403 without an active enrollment, 404 for a draft or unknown slug,
 * and on any other failure.
 */
export async function saveMyReview(
  slug: string,
  input: MyReviewInput,
): Promise<MyReview> {
  return apiFetch<MyReview>(
    `/api/courses/${encodeURIComponent(slug)}/reviews/mine/`,
    { method: "PUT", body: JSON.stringify(input) },
  );
}

/**
 * Needs no enrollment. Throws `ApiError` with status 404 when there is no
 * review or the course is a draft or unknown, and on any other failure.
 */
export async function deleteMyReview(slug: string): Promise<void> {
  await apiFetch(`/api/courses/${encodeURIComponent(slug)}/reviews/mine/`, {
    method: "DELETE",
  });
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
 * course) or a `publishProblems` body for a change a published course can't
 * take, 404 for an unknown id, 403 for anyone but an admin, and on any other
 * failure.
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
 * Throws `ApiError` with status 400 and a `publishProblems` body when the
 * course can't be published, 404 for an unknown id, 403 for anyone but an
 * admin, and on any other failure.
 */
export async function publishAdminCourse(id: string): Promise<AdminCourse> {
  return apiFetch<AdminCourse>(
    `/api/admin/courses/${encodeURIComponent(id)}/publish/`,
    { method: "POST" },
  );
}

/**
 * Takes the course out of the catalog; enrolled learners keep it. Throws
 * `ApiError` with status 404 for an unknown id, 403 for anyone but an admin,
 * and on any other failure.
 */
export async function unpublishAdminCourse(id: string): Promise<AdminCourse> {
  return apiFetch<AdminCourse>(
    `/api/admin/courses/${encodeURIComponent(id)}/unpublish/`,
    { method: "POST" },
  );
}

/**
 * Also deletes its curriculum and thumbnail. Throws `ApiError` with status 409
 * for a course anyone has enrolled in, bought or reviewed, 404 for an unknown
 * id, 403 for anyone but an admin, and on any other failure.
 */
export async function deleteAdminCourse(id: string): Promise<void> {
  await apiFetch(`/api/admin/courses/${encodeURIComponent(id)}/`, {
    method: "DELETE",
  });
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
 * key that isn't an upload for this course or an upload that never finished,
 * or a `publishProblems` body for removing a published course's thumbnail;
 * 404 for an unknown id, 403 for anyone but an admin, and on any other failure.
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
 * `FieldErrors` body for invalid input or a `publishProblems` body for an edit
 * a published course can't take, 404 for an unknown id, 403 for anyone but an
 * admin, and on any other failure. Positions count from 1, and one out of
 * range is clamped.
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
 * Only the fields given change. A blank `video_key` or `slides_key` removes
 * that file, and a replaced or removed file is deleted from storage. Throws
 * `ApiError` with status 400 and a `FieldErrors` body for invalid input
 * (including a key that isn't an upload of that kind for this lesson, or an
 * upload that never finished) or a `publishProblems` body for a change a
 * published course can't take, 404 for an unknown id, 403 for anyone but an
 * admin, and on any other failure.
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

/**
 * A presigned POST for a new video (MP4, up to 2 GB) or slides (PDF, up to
 * 100 MB). The lesson is unchanged until `updateAdminLesson` saves the key.
 * Throws `ApiError` with status 404 for an unknown id, 403 for anyone but an
 * admin, and on any other failure.
 */
export async function requestAdminLessonUpload(
  lessonId: string,
  kind: LessonFileKind,
): Promise<PresignedUpload> {
  return apiFetch<PresignedUpload>(
    `/api/admin/lessons/${encodeURIComponent(lessonId)}/uploads/`,
    { method: "POST", body: JSON.stringify({ kind }) },
  );
}

export const USER_ROLES = ["learner", "instructor", "admin"] as const;

export type UserRole = (typeof USER_ROLES)[number];

export function isUserRole(value: unknown): value is UserRole {
  return USER_ROLES.includes(value as UserRole);
}

export const ACCOUNT_STATUSES = ["active", "suspended", "deleted"] as const;

export type AccountStatus = (typeof ACCOUNT_STATUSES)[number];

export function isAccountStatus(value: unknown): value is AccountStatus {
  return ACCOUNT_STATUSES.includes(value as AccountStatus);
}

export const ADMIN_USER_SORTS = ["newest", "name", "email"] as const;

export type AdminUserSort = (typeof ADMIN_USER_SORTS)[number];

export function isAdminUserSort(value: unknown): value is AdminUserSort {
  return ADMIN_USER_SORTS.includes(value as AdminUserSort);
}

export type AdminUserSummary = {
  id: string;
  email: string;
  /** Blank when Clerk has no name for them. */
  name: string;
  /** Blank when Clerk has no image for them. */
  avatar_url: string;
  role: UserRole;
  status: AccountStatus;
  /** Revoked enrollments are not counted. */
  active_enrollment_count: number;
  created_at: string;
};

/**
 * Every user, 20 per page. `q` matches name or email; a blank `q` is no
 * filter, and a missing `status` means every status, deleted included. Throws
 * `ApiError` with status 404 for a page past the last, 403 for anyone but an
 * admin, and on any other failure.
 */
export async function fetchAdminUsers({
  q = "",
  role,
  status,
  sort = "newest",
  page = 1,
}: {
  q?: string;
  role?: UserRole;
  status?: AccountStatus;
  sort?: AdminUserSort;
  page?: number;
} = {}): Promise<Paginated<AdminUserSummary>> {
  const params = new URLSearchParams();
  if (q.trim()) params.set("q", q.trim());
  if (role) params.set("role", role);
  if (status) params.set("status", status);
  if (sort !== "newest") params.set("sort", sort);
  if (page > 1) params.set("page", String(page));

  const query = params.size ? `?${params}` : "";
  return apiFetch<Paginated<AdminUserSummary>>(`/api/admin/users/${query}`);
}

export type OrderStatus = "pending" | "paid" | "refunded" | "expired";

export type AdminUserOrder = {
  id: string;
  created_at: string;
  status: OrderStatus;
  total_cents: number;
  items: { title: string; unit_price_cents: number }[];
};

export type AdminUserReview = {
  id: string;
  rating: number;
  body: string;
  status: ReviewStatus;
  created_at: string;
  course: { id: string; title: string; slug: string; status: CourseStatus };
};

export type AdminUserDetail = Omit<
  AdminUserSummary,
  "active_enrollment_count"
> & {
  /** Null unless suspended. */
  suspended_at: string | null;
  /** Blank unless suspended. */
  suspension_reason: string;
  /** False once the person has deleted their Clerk login. */
  has_clerk_identity: boolean;
  /** Newest first. */
  orders: AdminUserOrder[];
  /** Newest first, hidden ones included. */
  reviews: AdminUserReview[];
};

/**
 * Any user, deleted ones included. Throws `ApiError` with status 404 for an
 * unknown or malformed id, 403 for anyone but an admin, and on any other
 * failure. Deduplicated per request.
 */
export const fetchAdminUser = cache(
  async (id: string): Promise<AdminUserDetail> =>
    apiFetch<AdminUserDetail>(`/api/admin/users/${encodeURIComponent(id)}/`),
);

/** The roles an admin can give; `instructor` is only ever moved off. */
export type AssignableRole = Exclude<UserRole, "instructor">;

/**
 * Changes the role and nothing else. Throws `ApiError` with status 400 and a
 * `FieldErrors` body when the target is the requester, `admin` is asked for a
 * user who isn't active, or the role isn't assignable; 404 for an unknown id,
 * 403 for anyone but an admin, and on any other failure.
 */
export async function updateAdminUserRole(
  id: string,
  role: AssignableRole,
): Promise<AdminUserDetail> {
  return apiFetch<AdminUserDetail>(
    `/api/admin/users/${encodeURIComponent(id)}/`,
    { method: "PATCH", body: JSON.stringify({ role }) },
  );
}

/**
 * Suspends an active or deleted user; their enrollments, orders and reviews
 * are kept. Throws `ApiError` with status 400 and a `FieldErrors` body for a
 * blank reason (`reason`) or a refused target (`non_field_errors`: yourself,
 * an admin, or a user already suspended), 404 for an unknown id, 403 for
 * anyone but an admin, and on any other failure.
 */
export async function suspendAdminUser(
  id: string,
  reason: string,
): Promise<AdminUserDetail> {
  return apiFetch<AdminUserDetail>(
    `/api/admin/users/${encodeURIComponent(id)}/suspend/`,
    { method: "POST", body: JSON.stringify({ reason }) },
  );
}

/**
 * Lifts a suspension: the user becomes active, or deleted when they have no
 * Clerk identity. Throws `ApiError` with status 400 and a `FieldErrors` body
 * (`non_field_errors`) for yourself or a user who isn't suspended, 404 for an
 * unknown id, 403 for anyone but an admin, and on any other failure.
 */
export async function reinstateAdminUser(id: string): Promise<AdminUserDetail> {
  return apiFetch<AdminUserDetail>(
    `/api/admin/users/${encodeURIComponent(id)}/reinstate/`,
    { method: "POST" },
  );
}

export type EnrollmentStatus = "active" | "revoked";

/** The sources an admin can grant; `purchase` comes only from an order. */
export type GrantSource = Exclude<EnrollmentSource, "purchase">;

export type AdminEnrollment = {
  id: string;
  course: { id: string; title: string; slug: string; status: CourseStatus };
  source: EnrollmentSource;
  status: EnrollmentStatus;
  /** Null unless the source is a purchase. */
  order_id: string | null;
  enrolled_at: string;
  /** Null unless revoked. */
  revoked_at: string | null;
  /** Of the course's current lessons. */
  completed_lesson_count: number;
  lesson_count: number;
};

/**
 * Every enrollment of a user, revoked ones and draft courses included; active
 * first, then newest. Throws `ApiError` with status 404 for an unknown or
 * malformed id, 403 for anyone but an admin, and on any other failure.
 */
export async function fetchAdminUserEnrollments(
  userId: string,
): Promise<AdminEnrollment[]> {
  return apiFetch<AdminEnrollment[]>(
    `/api/admin/users/${encodeURIComponent(userId)}/enrollments/`,
  );
}

/**
 * Enrolls a user of any status in any course, drafts included, without
 * payment. Throws `ApiError` with status 400 and a `FieldErrors` body for an
 * unknown course (`course_id`), a source other than manual or comp
 * (`source`), or a course the user already has a row for, revoked or not
 * (`non_field_errors`); 404 for an unknown user, 403 for anyone but an admin,
 * and on any other failure.
 */
export async function grantAdminEnrollment(
  userId: string,
  courseId: string,
  source: GrantSource,
): Promise<AdminEnrollment> {
  return apiFetch<AdminEnrollment>(
    `/api/admin/users/${encodeURIComponent(userId)}/enrollments/`,
    { method: "POST", body: JSON.stringify({ course_id: courseId, source }) },
  );
}

/**
 * Refunds nothing. Throws `ApiError` with status 400 and a `FieldErrors` body
 * (`non_field_errors`) when already revoked, 404 for an unknown id, 403 for
 * anyone but an admin, and on any other failure.
 */
export async function revokeAdminEnrollment(
  id: string,
): Promise<AdminEnrollment> {
  return apiFetch<AdminEnrollment>(
    `/api/admin/enrollments/${encodeURIComponent(id)}/revoke/`,
    { method: "POST" },
  );
}

/**
 * Brings the row back with its source, order and enrolled date. Throws
 * `ApiError` with status 400 and a `FieldErrors` body (`non_field_errors`)
 * when already active, 404 for an unknown id, 403 for anyone but an admin,
 * and on any other failure.
 */
export async function restoreAdminEnrollment(
  id: string,
): Promise<AdminEnrollment> {
  return apiFetch<AdminEnrollment>(
    `/api/admin/enrollments/${encodeURIComponent(id)}/restore/`,
    { method: "POST" },
  );
}
