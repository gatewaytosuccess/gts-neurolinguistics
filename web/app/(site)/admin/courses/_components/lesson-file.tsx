"use client";

import { useState, useTransition } from "react";

import type { LessonFileKind } from "@/lib/api";

import type { UploadResult, UploadTicket } from "../_lib/uploads";
import { FileUpload } from "./file-upload";

const KINDS = {
  video: {
    title: "Video",
    accept: ["video/mp4"],
    hint: "MP4, up to 2 GB.",
    uploadLabel: "Upload video",
    empty: "No video yet.",
    present: "Video uploaded.",
  },
  slides: {
    title: "Slides",
    accept: ["application/pdf"],
    hint: "PDF, up to 100 MB.",
    uploadLabel: "Upload slides",
    empty: "No slides yet.",
    present: "Slides uploaded.",
  },
} as const;

/** Whole seconds from the video's metadata; `null` if the browser can't read it. */
export function readVideoDuration(file: File): Promise<number | null> {
  return new Promise((resolve) => {
    const url = URL.createObjectURL(file);
    const video = document.createElement("video");
    const finish = (seconds: number | null) => {
      URL.revokeObjectURL(url);
      resolve(seconds);
    };
    video.preload = "metadata";
    video.onloadedmetadata = () => {
      const seconds = Math.round(video.duration);
      finish(Number.isFinite(seconds) && seconds > 0 ? seconds : null);
    };
    video.onerror = () => finish(null);
    video.src = url;
  });
}

/**
 * A lesson's video or slides: whether there is one, then Upload or Replace
 * and Remove. Rendered inside the lesson form, so it holds no form of its own.
 */
export function LessonFile({
  kind,
  url,
  requestUpload,
  save,
  remove,
  onChoose,
}: {
  kind: LessonFileKind;
  /** Blank when the lesson has no such file. */
  url: string;
  requestUpload: () => Promise<UploadTicket>;
  save: (key: string) => Promise<UploadResult>;
  remove: () => Promise<UploadResult>;
  onChoose?: (file: File) => void;
}) {
  const { title, accept, hint, uploadLabel, empty, present } = KINDS[kind];
  const [removing, startRemoving] = useTransition();
  const [removeError, setRemoveError] = useState<string>();
  const headingId = `lesson-${kind}-heading`;

  function handleRemove() {
    startRemoving(async () => {
      const result = await remove().catch(() => ({
        error: "The server isn't responding, so nothing was removed.",
      }));
      startRemoving(() => setRemoveError(result.error));
    });
  }

  return (
    <section aria-labelledby={headingId} className="measure">
      <h2 id={headingId} className="type-headline-sm">
        {title}
      </h2>

      <div className="mt-md flex flex-col gap-md">
        {!url ? (
          <p className="type-body-sm rounded-sm border border-dashed border-rule px-sm py-md text-meta-text">
            {empty}
          </p>
        ) : (
          <p className="type-body-sm rounded-sm border border-rule px-sm py-md text-accent-strong">
            {present}
          </p>
        )}

        <div className="flex flex-wrap items-start gap-md">
          <FileUpload
            id={`lesson-${kind}`}
            buttonLabel={url ? "Replace" : uploadLabel}
            accept={accept}
            hint={hint}
            requestUpload={requestUpload}
            save={save}
            onChoose={onChoose}
          />
          {url && (
            <button
              type="button"
              disabled={removing}
              onClick={handleRemove}
              className="type-label-md rounded-md border border-error bg-paper-raised px-md py-sm text-error hover:bg-error-subtle disabled:cursor-wait disabled:opacity-60"
            >
              {removing ? "Removing…" : "Remove"}
            </button>
          )}
        </div>

        {removeError && (
          <p
            role="alert"
            className="type-body-sm rounded-sm bg-error-subtle px-sm py-xs text-error"
          >
            {removeError}
          </p>
        )}
      </div>
    </section>
  );
}
