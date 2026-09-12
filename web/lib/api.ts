import { auth } from "@clerk/nextjs/server";

/*
 * The browser never talks to Django directly.
 *
 * Every call is made from the server with the Clerk session token attached, so
 * the token stays out of the bundle, the API's address stays a server-only
 * secret, and CORS never enters into it.
 */
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
    throw new ApiError(response.status, `${init.method ?? "GET"} ${path} failed`);
  }

  return (await response.json()) as T;
}

/**
 * The signed-in user's account row, or `null` if nobody is signed in.
 *
 * Also what closes the gap right after sign-up: Clerk redirects a new user
 * into the app before the `user.created` webhook necessarily lands, and this
 * endpoint provisions their row on the spot if it has not.
 */
export async function fetchCurrentUser(): Promise<CurrentUser | null> {
  const { userId } = await auth();
  if (!userId) return null;

  return apiFetch<CurrentUser>("/api/users/me/");
}
