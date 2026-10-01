"use client";

import {
  useActionState,
  useId,
  useRef,
  useState,
  type ReactNode,
  type RefObject,
} from "react";

import type { SuspensionState } from "../_lib/suspension";

type SuspendAction = (
  state: SuspensionState,
  formData: FormData,
) => Promise<SuspensionState>;

type ReinstateAction = (state: SuspensionState) => Promise<SuspensionState>;

const dangerClassName =
  "type-label-md rounded-sm border border-error bg-paper-raised px-sm py-xs text-error hover:bg-error-subtle";

const alertClassName =
  "type-body-sm rounded-sm bg-error-subtle px-sm py-xs text-error";

export function SuspendDialog({
  name,
  suspend,
  disabledReason,
  disabledBy,
}: {
  name: string;
  suspend: SuspendAction;
  /** Set when the user can't be suspended; the trigger is disabled with this hint. */
  disabledReason?: string;
  /** The id of a hint elsewhere on the page; the trigger is disabled and described by it. */
  disabledBy?: string;
}) {
  const { dialogRef, opened, open, close } = useDialog();
  const headingId = useId();

  return (
    <Trigger
      label="Suspend…"
      className={`${dangerClassName} disabled:cursor-not-allowed disabled:border-border-strong disabled:text-meta-text disabled:hover:bg-paper-raised`}
      onOpen={open}
      disabledReason={disabledReason}
      disabledBy={disabledBy}
    >
      <Modal dialogRef={dialogRef} headingId={headingId}>
        {/* Keyed by opening, so a reopened dialog starts blank. */}
        <SuspendForm
          key={opened}
          name={name}
          headingId={headingId}
          suspend={suspend}
          onCancel={close}
        />
      </Modal>
    </Trigger>
  );
}

function SuspendForm({
  name,
  headingId,
  suspend,
  onCancel,
}: {
  name: string;
  headingId: string;
  suspend: SuspendAction;
  onCancel: () => void;
}) {
  const [state, formAction, pending] = useActionState(suspend, {});
  const fieldId = useId();
  const hintId = `${fieldId}-hint`;
  const errorId = `${fieldId}-error`;

  return (
    // The reason reads its default from `state`: React resets the form after every submission.
    <form action={formAction} className="flex flex-col gap-md">
      <h2 id={headingId} className="type-headline-sm break-words">
        Suspend {name}?
      </h2>
      <p className="type-body-md">
        They&rsquo;ll be signed out of the platform until an admin reinstates
        them. Their enrollments, orders and reviews are kept.
      </p>
      <div>
        <label htmlFor={fieldId} className="type-label-md block">
          Reason
        </label>
        <textarea
          id={fieldId}
          name="reason"
          rows={4}
          required
          maxLength={500}
          defaultValue={state.reason}
          aria-describedby={
            state.reasonErrors ? `${hintId} ${errorId}` : hintId
          }
          {...(state.reasonErrors && { "aria-invalid": true })}
          className={`type-body-md mt-xs w-full rounded-sm border bg-paper-raised px-sm py-sm text-accent-strong ${
            state.reasonErrors ? "border-error" : "border-border-strong"
          }`}
        />
        <p id={hintId} className="type-caption mt-xs text-meta-text">
          Only admins see this. Up to 500 characters.
        </p>
        {state.reasonErrors && (
          <p id={errorId} className="type-body-sm mt-xs text-error">
            {state.reasonErrors.join(" ")}
          </p>
        )}
      </div>
      {state.error && (
        <p role="alert" className={alertClassName}>
          {state.error}
        </p>
      )}
      <div className="flex flex-wrap gap-md">
        <button
          type="submit"
          disabled={pending}
          className={`${dangerClassName} disabled:cursor-wait disabled:opacity-60`}
        >
          {pending ? "Suspending…" : "Suspend"}
        </button>
        <button type="button" onClick={onCancel} className="button-secondary">
          Cancel
        </button>
      </div>
    </form>
  );
}

export function ReinstateDialog({
  name,
  returnsToDeleted,
  reinstate,
  disabledBy,
}: {
  name: string;
  /** The user has no Clerk identity, so reinstating leaves them deleted. */
  returnsToDeleted: boolean;
  reinstate: ReinstateAction;
  /** The id of a hint elsewhere on the page; the trigger is disabled and described by it. */
  disabledBy?: string;
}) {
  const { dialogRef, opened, open, close } = useDialog();
  const headingId = useId();

  return (
    <Trigger
      label="Reinstate"
      className="button-secondary"
      onOpen={open}
      disabledBy={disabledBy}
    >
      <Modal dialogRef={dialogRef} headingId={headingId}>
        <ReinstateForm
          key={opened}
          name={name}
          headingId={headingId}
          returnsToDeleted={returnsToDeleted}
          reinstate={reinstate}
          onCancel={close}
        />
      </Modal>
    </Trigger>
  );
}

function ReinstateForm({
  name,
  headingId,
  returnsToDeleted,
  reinstate,
  onCancel,
}: {
  name: string;
  headingId: string;
  returnsToDeleted: boolean;
  reinstate: ReinstateAction;
  onCancel: () => void;
}) {
  const [state, formAction, pending] = useActionState(reinstate, {});

  return (
    <form action={formAction} className="flex flex-col gap-md">
      <h2 id={headingId} className="type-headline-sm break-words">
        Reinstate {name}?
      </h2>
      <p className="type-body-md">
        {returnsToDeleted
          ? "They have no Clerk identity, so they return to Deleted, not Active. Signing up again with their email brings them back."
          : "They can sign in to the platform again, with their enrollments, orders and reviews as they were."}
      </p>
      {state.error && (
        <p role="alert" className={alertClassName}>
          {state.error}
        </p>
      )}
      <div className="flex flex-wrap gap-md">
        <button
          type="submit"
          disabled={pending}
          className="button-secondary disabled:cursor-wait disabled:opacity-60"
        >
          {pending ? "Reinstating…" : "Reinstate"}
        </button>
        <button type="button" onClick={onCancel} className="button-secondary">
          Cancel
        </button>
      </div>
    </form>
  );
}

function useDialog() {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [opened, setOpened] = useState(0);

  return {
    dialogRef,
    opened,
    open() {
      setOpened((count) => count + 1);
      dialogRef.current?.showModal();
    },
    close() {
      dialogRef.current?.close();
    },
  };
}

function Trigger({
  label,
  className,
  onOpen,
  disabledReason,
  disabledBy,
  children,
}: {
  label: string;
  className: string;
  onOpen: () => void;
  disabledReason?: string;
  disabledBy?: string;
  children: ReactNode;
}) {
  const hintId = useId();
  const disabled = Boolean(disabledReason || disabledBy);

  return (
    <div className="mt-lg flex flex-wrap items-center gap-md">
      <button
        type="button"
        onClick={onOpen}
        disabled={disabled}
        aria-describedby={disabledReason ? hintId : disabledBy}
        className={className}
      >
        {label}
      </button>
      {disabledReason && (
        <p id={hintId} className="type-caption text-meta-text">
          {disabledReason}
        </p>
      )}
      {!disabled && children}
    </div>
  );
}

function Modal({
  dialogRef,
  headingId,
  children,
}: {
  dialogRef: RefObject<HTMLDialogElement | null>;
  headingId: string;
  children: ReactNode;
}) {
  return (
    <dialog
      ref={dialogRef}
      aria-labelledby={headingId}
      className="m-auto w-[calc(100%-2*var(--spacing-md))] max-w-[34rem] rounded-lg bg-paper-raised p-lg text-accent-strong shadow-[0_8px_24px_rgb(38_30_15/0.16)] transition-[opacity,translate] duration-200 ease-out backdrop:bg-accent-strong/40 starting:open:translate-y-xs starting:open:opacity-0"
    >
      {children}
    </dialog>
  );
}
