import { auth } from "@clerk/nextjs/server";

// Server-only: the browser never calls Django directly.
const API_BASE_URL = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
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
    );
  }

  return (await response.json()) as T;
}

/**
 * `null` if nobody is signed in. Throws if the API is unreachable or returns
 * non-2xx. Safe right after sign-up: the API provisions a missing row.
 */
export async function fetchCurrentUser(): Promise<CurrentUser | null> {
  const { userId } = await auth();
  if (!userId) return null;

  return apiFetch<CurrentUser>("/api/users/me/");
}

/** Published courses, newest first. Throws if the API is unreachable or returns non-2xx. */
export async function fetchCourses(): Promise<Paginated<CourseSummary>> {
  return publicFetch<Paginated<CourseSummary>>("/api/courses/");
}
