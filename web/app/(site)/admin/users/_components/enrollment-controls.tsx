"use client";

import { useActionState, useId } from "react";

import type { CourseStatus, GrantSource } from "@/lib/api";

import type { EnrollmentActionState } from "../_lib/enrollment";
import { Modal, useDialog } from "./dialog";

type RowAction = () => Promise<EnrollmentActionState>;

type GrantAction = (
  state: EnrollmentActionState,
  formData: FormData,
) => Promise<EnrollmentActionState>;

const dangerClassName =
  "type-label-md whitespace-nowrap rounded-sm border border-error bg-paper-raised px-sm py-xs text-error hover:bg-error-subtle disabled:cursor-wait disabled:opacity-60";

const alertClassName =
  "type-body-sm rounded-sm bg-error-subtle px-sm py-xs text-error";

export function RevokeDialog({
  name,
  courseTitle,
  isPurchase,
  revoke,
}: {
  name: string;
  courseTitle: string;
  isPurchase: boolean;
  revoke: RowAction;
}) {
  const { dialogRef, opened, open, close } = useDialog();
  const headingId = useId();

  return (
    <>
      <button type="button" onClick={open} className={dangerClassName}>
        Revoke…
      </button>
      <Modal dialogRef={dialogRef} headingId={headingId}>
        <RevokeForm
          key={opened}
          name={name}
          courseTitle={courseTitle}
          isPurchase={isPurchase}
          headingId={headingId}
          revoke={revoke}
          onCancel={close}
        />
      </Modal>
    </>
  );
}

function RevokeForm({
  name,
  courseTitle,
  isPurchase,
  headingId,
  revoke,
  onCancel,
}: {
  name: string;
  courseTitle: string;
  isPurchase: boolean;
  headingId: string;
  revoke: RowAction;
  onCancel: () => void;
}) {
  const [state, formAction, pending] = useActionState(revoke, {});

  return (
    <form action={formAction} className="flex flex-col gap-md">
      <h2 id={headingId} className="type-headline-sm break-words">
        Revoke {courseTitle}?
      </h2>
      <p className="type-body-md">
        {name} loses access to this course. Restoring it later brings it back as
        it was.
        {isPurchase && " This does not refund the order."}
      </p>
      {state.error && (
        <p role="alert" className={alertClassName}>
          {state.error}
        </p>
      )}
      <div className="flex flex-wrap gap-md">
        <button type="submit" disabled={pending} className={dangerClassName}>
          {pending ? "Revoking…" : "Revoke"}
        </button>
        <button type="button" onClick={onCancel} className="button-secondary">
          Cancel
        </button>
      </div>
    </form>
  );
}

export function RestoreButton({ restore }: { restore: RowAction }) {
  const [state, formAction, pending] = useActionState(restore, {});

  return (
    <form action={formAction}>
      <button
        type="submit"
        disabled={pending}
        className="type-label-md whitespace-nowrap rounded-sm border border-primary bg-paper-raised px-sm py-xs text-primary hover:bg-paper-dim disabled:cursor-wait disabled:opacity-60"
      >
        {pending ? "Restoring…" : "Restore"}
      </button>
      {state.error && (
        <p role="alert" className={`${alertClassName} mt-xs max-w-[16rem]`}>
          {state.error}
        </p>
      )}
    </form>
  );
}

export type GrantableCourse = {
  id: string;
  title: string;
  status: CourseStatus;
};

const SOURCE_OPTIONS: { value: GrantSource; label: string; hint: string }[] = [
  {
    value: "manual",
    label: "Manual",
    hint: "A support fix: they paid another way, or a purchase didn’t enroll them.",
  },
  {
    value: "comp",
    label: "Comp",
    hint: "Access given away: staff, press or a beta tester.",
  },
];

export function GrantForm({
  courses,
  grant,
}: {
  courses: GrantableCourse[];
  grant: GrantAction;
}) {
  const [state, formAction, pending] = useActionState(grant, {});
  const selectId = useId();
  const published = courses.filter((course) => course.status === "published");
  const drafts = courses.filter((course) => course.status === "draft");

  return (
    // Choices read their defaults from `state`: React resets the form after every submission.
    <form
      action={formAction}
      className="measure mt-lg flex flex-col gap-md rounded-sm border border-rule bg-paper-raised p-md"
    >
      <h3 className="type-label-lg">Grant a course</h3>
      <div>
        <label htmlFor={selectId} className="type-label-md block">
          Course
        </label>
        <select
          // Remounts when a refused grant comes back, so the select shows its choice.
          key={state.courseId}
          id={selectId}
          name="course_id"
          required
          defaultValue={state.courseId ?? ""}
          className="type-body-md mt-xs w-full rounded-sm border border-border-strong bg-paper-raised px-sm py-sm text-accent-strong"
        >
          <option value="" disabled>
            Choose a course
          </option>
          {published.length > 0 && (
            <optgroup label="Published">
              {published.map((course) => (
                <option key={course.id} value={course.id}>
                  {course.title}
                </option>
              ))}
            </optgroup>
          )}
          {drafts.length > 0 && (
            <optgroup label="Draft">
              {drafts.map((course) => (
                <option key={course.id} value={course.id}>
                  {course.title} (Draft)
                </option>
              ))}
            </optgroup>
          )}
        </select>
      </div>
      <fieldset key={state.source}>
        <legend className="type-label-md">Source</legend>
        <div className="mt-xs flex flex-col gap-sm">
          {SOURCE_OPTIONS.map((option) => (
            <label key={option.value} className="flex items-start gap-sm">
              <input
                type="radio"
                name="source"
                value={option.value}
                required
                defaultChecked={state.source === option.value}
                className="mt-[0.3rem] accent-primary"
              />
              <span>
                <span className="type-body-md block">{option.label}</span>
                <span className="type-caption block text-meta-text">
                  {option.hint}
                </span>
              </span>
            </label>
          ))}
        </div>
      </fieldset>
      {state.error && (
        <p role="alert" className={alertClassName}>
          {state.error}
        </p>
      )}
      <div>
        <button
          type="submit"
          disabled={pending}
          className="button-secondary disabled:cursor-wait disabled:opacity-60"
        >
          {pending ? "Granting…" : "Grant"}
        </button>
      </div>
    </form>
  );
}
