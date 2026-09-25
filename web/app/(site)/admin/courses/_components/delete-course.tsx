"use client";

import { useActionState } from "react";

import type { CourseStatusState } from "../_lib/course-status";

type StatusAction = (state: CourseStatusState) => Promise<CourseStatusState>;

const dangerClassName =
  "type-label-md rounded-sm border border-error bg-paper-raised px-sm py-xs text-error hover:bg-error-subtle disabled:cursor-wait disabled:opacity-60";

const alertClassName =
  "type-body-sm rounded-sm bg-error-subtle px-sm py-xs text-error";

// A <details> disclosure, so confirming needs no JavaScript.
export function DeleteCourse({
  title,
  published,
  remove,
  unpublish,
}: {
  title: string;
  published: boolean;
  remove: StatusAction;
  unpublish: StatusAction;
}) {
  const [state, removeAction, removing] = useActionState(remove, {});
  const [unpublishState, unpublishAction, unpublishing] = useActionState(
    unpublish,
    {},
  );

  return (
    <details className="group mt-md">
      <summary
        className={`${dangerClassName} inline-block cursor-pointer list-none group-open:bg-error-subtle [&::-webkit-details-marker]:hidden`}
      >
        Delete this course
      </summary>
      <div className="measure mt-sm flex flex-col gap-sm rounded-sm border border-error bg-paper-raised p-sm">
        <p className="type-body-sm">
          Delete &ldquo;{title}&rdquo;? Its modules and lessons are deleted too,
          and this can&rsquo;t be undone.
        </p>
        <form action={removeAction}>
          <button type="submit" disabled={removing} className={dangerClassName}>
            {removing ? "Deleting…" : "Delete course"}
          </button>
        </form>
        {state.error && (
          <p role="alert" className={alertClassName}>
            {state.error}
          </p>
        )}
        {state.hasHistory && (
          <div role="alert" className={alertClassName}>
            <p>
              People have enrolled in, bought or reviewed this course, so it
              can&rsquo;t be deleted.{" "}
              {published
                ? "Unpublish it instead: it leaves the catalog, and enrolled learners keep it."
                : "It's a draft, so it's already out of the catalog."}
            </p>
            {published && (
              <form action={unpublishAction} className="mt-sm">
                <button
                  type="submit"
                  disabled={unpublishing}
                  className="button-secondary disabled:cursor-wait disabled:opacity-60"
                >
                  {unpublishing ? "Unpublishing…" : "Unpublish instead"}
                </button>
              </form>
            )}
            {unpublishState.error && (
              <p className="mt-sm">{unpublishState.error}</p>
            )}
          </div>
        )}
      </div>
    </details>
  );
}
