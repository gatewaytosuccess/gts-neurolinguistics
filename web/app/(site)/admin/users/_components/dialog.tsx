"use client";

import { useRef, useState, type ReactNode, type RefObject } from "react";

/** `opened` counts openings: key a dialog's form by it so each opening starts blank. */
export function useDialog() {
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

export function Modal({
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
