import { ApiError, saveLessonProgress } from "@/lib/api";

/**
 * Saves `{lessonId, position_seconds}` for the signed-in learner. A route
 * handler, not a server action, so `navigator.sendBeacon` can reach it as the
 * tab closes. Answers 204, or the course API's status when it refuses.
 */
export async function POST(request: Request) {
  // Read as text: a beacon sends its JSON as text/plain.
  let body: { lessonId?: unknown; position_seconds?: unknown };
  try {
    body = JSON.parse(await request.text());
  } catch {
    return new Response(null, { status: 400 });
  }
  const { lessonId, position_seconds } = body ?? {};
  if (typeof lessonId !== "string" || typeof position_seconds !== "number") {
    return new Response(null, { status: 400 });
  }

  try {
    await saveLessonProgress(lessonId, { position_seconds });
  } catch (error) {
    return new Response(null, {
      status: error instanceof ApiError ? error.status : 502,
    });
  }
  return new Response(null, { status: 204 });
}
