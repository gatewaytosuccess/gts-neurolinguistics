"use client";

import { useActionState } from "react";

import type { CourseStatusState } from "../_lib/course-status";
import { PublishProblems } from "./publish-problems";

type StatusAction = (state: CourseStatusState) => Promise<CourseStatusState>;

export function PublishControl({
  published,
  publish,
  unpublish,
}: {
  published: boolean;
  publish: StatusAction;
  unpublish: StatusAction;
}) {
  // Keyed by status, so a status change remounts and clears the last answer.
  return published ? (
    <StatusForm
      key="unpublish"
      action={unpublish}
      label="Unpublish"
      pendingLabel="Unpublishing…"
      hint="Takes the course out of the catalog. Enrolled learners keep it."
    />
  ) : (
    <StatusForm
      key="publish"
      action={publish}
      label="Publish"
      pendingLabel="Publishing…"
      hint="Puts the course in the catalog."
    />
  );
}

function StatusForm({
  action,
  label,
  pendingLabel,
  hint,
}: {
  action: StatusAction;
  label: string;
  pendingLabel: string;
  hint: string;
}) {
  const [state, formAction, pending] = useActionState(action, {});

  return (
    <form
      action={formAction}
      className="mt-md flex flex-wrap items-center gap-md"
    >
      <button
        type="submit"
        disabled={pending}
        className="button-secondary disabled:cursor-wait disabled:opacity-60"
      >
        {pending ? pendingLabel : label}
      </button>
      <p className="type-caption text-meta-text">{hint}</p>
      {state.error && (
        <p
          role="alert"
          className="type-body-sm measure basis-full rounded-sm bg-error-subtle px-sm py-xs text-error"
        >
          {state.error}
        </p>
      )}
      {state.problems && (
        <PublishProblems refused="publish" problems={state.problems} />
      )}
    </form>
  );
}
