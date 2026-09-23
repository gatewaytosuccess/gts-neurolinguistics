"use client";

import { useActionState, type ReactNode } from "react";

import type {
  CourseDetailsState,
  CourseDetailsValues,
} from "../_lib/course-details";

const fieldClassName =
  "type-body-md mt-xs w-full rounded-sm border bg-paper-raised px-sm py-sm text-accent-strong placeholder:text-meta-text read-only:bg-paper-dim";

export function CourseDetailsForm({
  action,
  initialState,
  slugLocked = false,
  submitLabel,
}: {
  action: (
    state: CourseDetailsState,
    formData: FormData,
  ) => Promise<CourseDetailsState>;
  initialState: CourseDetailsState;
  slugLocked?: boolean;
  submitLabel: string;
}) {
  const [state, formAction, pending] = useActionState(action, initialState);
  const { values, errors } = state;

  return (
    // Fields read their defaults from `state`: React resets the form after every submission.
    <form action={formAction} className="measure mt-lg flex flex-col gap-lg">
      {errors.form && (
        <p
          role="alert"
          className="type-body-sm rounded-sm bg-error-subtle px-sm py-sm text-error"
        >
          {errors.form.join(" ")}
        </p>
      )}

      <Field name="title" label="Title" errors={errors.title}>
        {(props) => (
          <input
            {...props}
            type="text"
            required
            maxLength={255}
            defaultValue={values.title}
          />
        )}
      </Field>

      <Field
        name="slug"
        label="Slug"
        hint={
          slugLocked
            ? "The slug can't change while the course is published."
            : "Lowercase letters, numbers and hyphens. Leave it blank to generate it from the title."
        }
        errors={errors.slug}
      >
        {({ name, ...props }) => (
          <input
            {...props}
            // Unnamed when locked, so the slug is never sent.
            name={slugLocked ? undefined : name}
            type="text"
            readOnly={slugLocked}
            maxLength={255}
            placeholder={slugLocked ? undefined : "Generated from the title"}
            defaultValue={values.slug}
          />
        )}
      </Field>

      <Field
        name="price"
        label="Price (USD)"
        hint="In dollars, such as 129 or 129.99."
        errors={errors.price}
      >
        {(props) => (
          <input
            {...props}
            type="text"
            inputMode="decimal"
            required
            defaultValue={values.price}
          />
        )}
      </Field>

      <Field name="description" label="Description" errors={errors.description}>
        {(props) => (
          <textarea {...props} rows={6} defaultValue={values.description} />
        )}
      </Field>

      <div className="flex flex-wrap items-center gap-md">
        <button
          type="submit"
          disabled={pending}
          className="button-primary disabled:cursor-wait disabled:opacity-60"
        >
          {pending ? "Saving…" : submitLabel}
        </button>
        {state.saved && !pending && (
          <p role="status" className="type-body-sm text-success">
            Saved.
          </p>
        )}
      </div>
    </form>
  );
}

type ControlProps = {
  id: string;
  name: keyof CourseDetailsValues;
  className: string;
  "aria-invalid"?: true;
  "aria-describedby"?: string;
};

function Field({
  name,
  label,
  hint,
  errors,
  children,
}: {
  name: keyof CourseDetailsValues;
  label: string;
  hint?: string;
  errors?: string[];
  children: (props: ControlProps) => ReactNode;
}) {
  const id = `course-${name}`;
  const hintId = `${id}-hint`;
  const errorId = `${id}-error`;
  const describedBy = [hint && hintId, errors && errorId]
    .filter(Boolean)
    .join(" ");

  return (
    <div>
      <label htmlFor={id} className="type-label-md block">
        {label}
      </label>
      {children({
        id,
        name,
        className: `${fieldClassName} ${errors ? "border-error" : "border-border-strong"}`,
        ...(errors && { "aria-invalid": true }),
        ...(describedBy && { "aria-describedby": describedBy }),
      })}
      {hint && (
        <p id={hintId} className="type-caption mt-xs text-meta-text">
          {hint}
        </p>
      )}
      {errors && (
        <p id={errorId} className="type-body-sm mt-xs text-error">
          {errors.join(" ")}
        </p>
      )}
    </div>
  );
}
