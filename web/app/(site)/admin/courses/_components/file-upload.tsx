"use client";

import { useRef, useState } from "react";

import type { PresignedUpload } from "@/lib/api";

import type { UploadResult, UploadTicket } from "../_lib/uploads";

type Phase =
  | { kind: "idle" }
  | { kind: "preparing" }
  | { kind: "uploading"; fraction: number }
  | { kind: "saving" }
  | { kind: "saved" }
  | { kind: "error"; message: string };

// S3's error codes for the presigned POST's policy conditions.
const S3_ERRORS: Record<string, string> = {
  EntityTooLarge: "This file is over the size limit.",
  EntityTooSmall: "This file is empty.",
};

function s3ErrorMessage(responseText: string): string {
  const error = new DOMParser().parseFromString(
    responseText,
    "application/xml",
  );
  const code = error.querySelector("Code")?.textContent;
  if (code && S3_ERRORS[code]) return S3_ERRORS[code];
  // A failed policy condition is an AccessDenied whose message names the field.
  if (error.querySelector("Message")?.textContent?.includes("$Content-Type")) {
    return "This file isn't a type this upload accepts.";
  }
  return "Storage refused the file. Try again.";
}

/** Rejects with a message to show. */
function postToS3(
  upload: PresignedUpload,
  file: File,
  onProgress: (fraction: number) => void,
): Promise<void> {
  const body = new FormData();
  for (const [name, value] of Object.entries(upload.fields)) {
    // The file's own type, so S3's policy refuses a file of the wrong type.
    body.append(name, name === "Content-Type" ? file.type : value);
  }
  // S3 ignores every field after the file.
  body.append("file", file);

  return new Promise((resolve, reject) => {
    // XHR, not fetch: fetch reports no upload progress.
    const request = new XMLHttpRequest();
    request.open("POST", upload.url);
    request.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(event.loaded / event.total);
    };
    request.onload = () => {
      if (request.status >= 200 && request.status < 300) resolve();
      else reject(s3ErrorMessage(request.responseText));
    };
    // S3 can reset the connection on an oversized file instead of answering.
    request.onerror = () =>
      reject(
        "The upload didn't finish. Check the file is within the size limit and try again.",
      );
    request.send(body);
  });
}

/**
 * Picks a file, uploads it straight to S3 through a presigned POST, then saves
 * its key. The file's MIME type is what `requestUpload` receives and what S3
 * checks. `onChoose` runs with the file before anything is uploaded.
 */
export function FileUpload({
  id,
  buttonLabel,
  accept,
  hint,
  requestUpload,
  save,
  onChoose,
}: {
  id: string;
  buttonLabel: string;
  accept: readonly string[];
  hint: string;
  requestUpload: (contentType: string) => Promise<UploadTicket>;
  save: (key: string) => Promise<UploadResult>;
  onChoose?: (file: File) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [phase, setPhase] = useState<Phase>({ kind: "idle" });
  const busy =
    phase.kind === "preparing" ||
    phase.kind === "uploading" ||
    phase.kind === "saving";

  async function upload(file: File) {
    onChoose?.(file);
    setPhase({ kind: "preparing" });
    const ticket = await requestUpload(file.type).catch(() => ({
      error: "The server isn't responding, so nothing was uploaded.",
    }));
    if ("error" in ticket) {
      setPhase({ kind: "error", message: ticket.error });
      return;
    }

    setPhase({ kind: "uploading", fraction: 0 });
    try {
      await postToS3(ticket.upload, file, (fraction) =>
        setPhase({ kind: "uploading", fraction }),
      );
    } catch (message) {
      setPhase({ kind: "error", message: String(message) });
      return;
    }

    setPhase({ kind: "saving" });
    const result = await save(ticket.upload.key).catch(() => ({
      error: "The server isn't responding, so the upload wasn't saved.",
    }));
    setPhase(
      result.error
        ? { kind: "error", message: result.error }
        : { kind: "saved" },
    );
  }

  const hintId = `${id}-hint`;

  return (
    <div>
      <input
        ref={inputRef}
        id={id}
        type="file"
        accept={accept.join(",")}
        hidden
        onChange={(event) => {
          const file = event.target.files?.[0];
          // Cleared so choosing the same file again still fires a change.
          event.target.value = "";
          if (file) void upload(file);
        }}
      />
      <button
        type="button"
        disabled={busy}
        aria-describedby={hintId}
        onClick={() => inputRef.current?.click()}
        className="button-secondary disabled:cursor-wait"
      >
        {buttonLabel}
      </button>
      <p id={hintId} className="type-caption mt-xs text-meta-text">
        {hint}
      </p>

      <div aria-live="polite" className="mt-sm">
        {phase.kind === "preparing" && (
          <p className="type-body-sm text-meta-text">Preparing the upload…</p>
        )}
        {phase.kind === "uploading" && (
          <ProgressBar fraction={phase.fraction} />
        )}
        {phase.kind === "saving" && (
          <p className="type-body-sm text-meta-text">Saving…</p>
        )}
        {phase.kind === "saved" && (
          <p role="status" className="type-body-sm text-success">
            Uploaded.
          </p>
        )}
      </div>
      {phase.kind === "error" && (
        <p
          role="alert"
          className="type-body-sm mt-sm rounded-sm bg-error-subtle px-sm py-xs text-error"
        >
          {phase.message}
        </p>
      )}
    </div>
  );
}

function ProgressBar({ fraction }: { fraction: number }) {
  const percent = Math.round(fraction * 100);
  return (
    <div className="flex items-center gap-sm">
      <div
        role="progressbar"
        aria-label="Upload progress"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percent}
        className="h-2 w-full max-w-[320px] overflow-hidden rounded-full bg-paper-dim"
      >
        <div
          className="h-full bg-primary transition-[width]"
          style={{ width: `${percent}%` }}
        />
      </div>
      <span className="type-data-md text-meta-text">{percent}%</span>
    </div>
  );
}
