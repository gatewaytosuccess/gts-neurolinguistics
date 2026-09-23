"use client";

import { useActionState, type ReactNode } from "react";

import type { OutlineActionState } from "../_lib/curriculum";

/** A curriculum control's form, with its error shown under it. */
export function OutlineForm({
  action,
  className = "",
  children,
}: {
  action: (
    state: OutlineActionState,
    formData: FormData,
  ) => Promise<OutlineActionState>;
  className?: string;
  children: ReactNode;
}) {
  const [state, formAction, pending] = useActionState(action, {});

  return (
    <form action={formAction} aria-busy={pending} className={className}>
      {/* Disabled while pending, so a double click can't move an item twice. */}
      <fieldset disabled={pending} className="contents">
        {children}
      </fieldset>
      {state.error && (
        <p
          role="alert"
          className="type-body-sm basis-full rounded-sm bg-error-subtle px-sm py-xs text-error"
        >
          {state.error}
        </p>
      )}
    </form>
  );
}
