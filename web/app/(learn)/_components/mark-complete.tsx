"use client";

import { useState, useTransition } from "react";

import { setLessonCompleted } from "../_lib/progress-actions";
import { useOutline } from "./outline-context";

/** Renders nothing unless the outline says the caller is enrolled. */
export function MarkComplete({ lessonId }: { lessonId: string }) {
  const outline = useOutline();
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string>();

  if (outline?.access !== "enrolled") return null;
  const completed = outline.modules
    .flatMap((module) => module.lessons)
    .some((lesson) => lesson.id === lessonId && lesson.completed);

  function save(next: boolean) {
    setError(undefined);
    startTransition(async () => {
      const result = await setLessonCompleted(lessonId, next);
      setError(result.error);
    });
  }

  return (
    <div className="flex flex-col items-center gap-xs">
      {completed ? (
        <div className="flex flex-wrap items-center justify-center gap-x-md gap-y-xs">
          <span className="type-label-lg flex items-center gap-xs text-dark-success">
            <svg
              viewBox="0 0 16 16"
              width={16}
              height={16}
              fill="none"
              stroke="currentColor"
              strokeWidth={1.75}
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden
            >
              <path d="M3 8.5l3.25 3.25L13 5" />
            </svg>
            Completed
          </span>
          <button
            type="button"
            onClick={() => save(false)}
            disabled={pending}
            className="type-label-md text-dark-primary underline hover:text-dark-primary-strong disabled:cursor-wait disabled:opacity-60"
          >
            {pending ? "Saving…" : "Mark incomplete"}
          </button>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => save(true)}
          disabled={pending}
          className="button-primary-dark disabled:cursor-wait disabled:opacity-60"
        >
          {pending ? "Saving…" : "Mark complete"}
        </button>
      )}
      {error && (
        <p
          role="alert"
          className="type-body-sm rounded-sm bg-dark-error-subtle px-sm py-xs text-dark-error"
        >
          {error}
        </p>
      )}
    </div>
  );
}
