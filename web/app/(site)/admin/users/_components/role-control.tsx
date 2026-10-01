"use client";

import Link from "next/link";
import {
  useActionState,
  useRef,
  useState,
  useSyncExternalStore,
  type FormEvent,
} from "react";

import type { AccountStatus, AssignableRole, UserRole } from "@/lib/api";

import { ROLE_LABELS } from "../_lib/format";
import {
  isAssignableRole,
  roleChangeEffect,
  SELF_HINT_ID,
  type RoleChangeState,
} from "../_lib/role-change";

type RoleAction = (
  state: RoleChangeState,
  formData: FormData,
) => Promise<RoleChangeState>;

const fieldClassName =
  "type-body-md rounded-sm border border-border-strong bg-paper-raised px-sm py-sm text-accent-strong disabled:cursor-not-allowed disabled:opacity-60";

const noSubscription = () => () => {};

/**
 * Save opens a confirm dialog. Without JavaScript, Save comes back with the
 * same confirmation inline and a second submit makes the change.
 */
export function RoleControl({
  userId,
  name,
  role,
  status,
  isSelf,
  action,
}: {
  userId: string;
  name: string;
  role: UserRole;
  status: AccountStatus;
  isSelf: boolean;
  action: RoleAction;
}) {
  const [state, formAction, pending] = useActionState(action, {});
  const [selected, setSelected] = useState<UserRole>(role);
  const dialogRef = useRef<HTMLDialogElement>(null);
  const hydrated = useSyncExternalStore(
    noSubscription,
    () => true,
    () => false,
  );

  const adminBlocked = status !== "active" && role !== "admin";
  // Enabled on the server render, so Save works before and without JavaScript.
  const unchanged = hydrated && selected === role;

  function confirmFirst(event: FormEvent<HTMLFormElement>) {
    const submitter = (event.nativeEvent as SubmitEvent).submitter;
    if (submitter?.getAttribute("name") === "confirmed") {
      dialogRef.current?.close();
      return;
    }
    event.preventDefault();
    if (isAssignableRole(selected) && selected !== role) {
      dialogRef.current?.showModal();
    }
  }

  return (
    <div>
      <form
        action={formAction}
        onSubmit={confirmFirst}
        className="flex flex-wrap items-center gap-sm"
      >
        <select
          name="role"
          aria-label="Role"
          value={selected}
          onChange={(event) => setSelected(event.target.value as UserRole)}
          disabled={isSelf || pending}
          className={fieldClassName}
        >
          <option value="learner">{ROLE_LABELS.learner}</option>
          {role === "instructor" && (
            <option value="instructor" disabled>
              {ROLE_LABELS.instructor}
            </option>
          )}
          <option value="admin" disabled={adminBlocked}>
            {ROLE_LABELS.admin}
          </option>
        </select>
        <button
          type="submit"
          disabled={isSelf || pending || unchanged}
          className="button-secondary disabled:opacity-60"
        >
          {pending ? "Saving…" : "Save"}
        </button>
        {isSelf ? (
          <p id={SELF_HINT_ID} className="type-caption text-meta-text">
            You can&rsquo;t change your own role or status.
          </p>
        ) : (
          adminBlocked && (
            <p className="type-caption text-meta-text">
              Admin is for active users only.
            </p>
          )
        )}

        {isAssignableRole(selected) && (
          <dialog
            ref={dialogRef}
            aria-labelledby="role-dialog-heading"
            className="m-auto w-[calc(100%-2*var(--spacing-md))] max-w-[480px] rounded-lg bg-paper-raised p-lg text-accent-strong shadow-[0_8px_24px_rgb(38_30_15/0.16)] backdrop:bg-accent-strong/40"
          >
            <h3 id="role-dialog-heading" className="type-headline-sm">
              Make {name} {article(selected)} {selected}?
            </h3>
            <p className="type-body-md mt-sm">
              {roleChangeEffect(name, role, selected)}
            </p>
            <div className="mt-lg flex flex-wrap gap-sm">
              <button
                type="submit"
                name="confirmed"
                value="yes"
                className="button-secondary"
              >
                Change role
              </button>
              <button
                type="button"
                onClick={() => dialogRef.current?.close()}
                className="type-label-md px-sm py-sm text-primary hover:underline"
              >
                Cancel
              </button>
            </div>
          </dialog>
        )}
      </form>

      {state.confirming && (
        <form
          action={formAction}
          className="measure mt-sm rounded-sm border border-border-strong bg-paper-raised p-sm"
        >
          <input type="hidden" name="role" value={state.confirming} />
          <p className="type-body-sm">
            {roleChangeEffect(name, role, state.confirming)}
          </p>
          <div className="mt-sm flex flex-wrap items-center gap-sm">
            <button
              type="submit"
              name="confirmed"
              value="yes"
              disabled={pending}
              className="button-secondary disabled:cursor-wait disabled:opacity-60"
            >
              Change role
            </button>
            <Link
              href={`/admin/users/${userId}`}
              className="type-label-md text-primary hover:underline"
            >
              Cancel
            </Link>
          </div>
        </form>
      )}

      {state.error && (
        <p
          role="alert"
          className="type-body-sm measure mt-sm rounded-sm bg-error-subtle px-sm py-xs text-error"
        >
          {state.error}
        </p>
      )}
    </div>
  );
}

function article(role: AssignableRole) {
  return role === "admin" ? "an" : "a";
}
