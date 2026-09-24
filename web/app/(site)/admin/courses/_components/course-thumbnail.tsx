"use client";

import { useActionState } from "react";

import type { UploadResult, UploadTicket } from "../_lib/uploads";
import { FileUpload } from "./file-upload";

const THUMBNAIL_TYPES = ["image/jpeg", "image/png", "image/webp"] as const;

const frameClassName = "aspect-video w-full max-w-[480px] rounded-xs";

export function CourseThumbnail({
  url,
  removable,
  requestUpload,
  save,
  remove,
}: {
  /** Blank when there's no thumbnail. */
  url: string;
  removable: boolean;
  requestUpload: (contentType: string) => Promise<UploadTicket>;
  save: (key: string) => Promise<UploadResult>;
  remove: () => Promise<UploadResult>;
}) {
  const [removeState, removeAction, removing] = useActionState(
    () => remove(),
    {},
  );

  return (
    <div className="mt-lg flex flex-col gap-md">
      {url ? (
        // CloudFront's domain is a Django setting, so next/image has no host to allowlist.
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={url}
          alt="Current thumbnail"
          className={`${frameClassName} bg-paper-dim object-cover`}
        />
      ) : (
        <div
          className={`${frameClassName} flex items-center justify-center border border-dashed border-rule bg-paper-dim`}
        >
          <p className="type-body-sm text-meta-text">No thumbnail yet.</p>
        </div>
      )}

      <div className="flex flex-wrap items-start gap-md">
        <FileUpload
          id="course-thumbnail"
          buttonLabel={url ? "Replace" : "Upload thumbnail"}
          accept={THUMBNAIL_TYPES}
          hint="JPEG, PNG or WebP, up to 5 MB. 16:9 suits the catalog cards, such as 1600 × 900."
          requestUpload={requestUpload}
          save={save}
        />
        {url && removable && (
          <form action={removeAction}>
            <button
              type="submit"
              disabled={removing}
              className="type-label-md rounded-md border border-error bg-paper-raised px-md py-sm text-error hover:bg-error-subtle disabled:cursor-wait disabled:opacity-60"
            >
              {removing ? "Removing…" : "Remove"}
            </button>
          </form>
        )}
      </div>

      {url && !removable && (
        <p className="type-caption text-meta-text">
          A published course must keep a thumbnail: it can be replaced, not
          removed.
        </p>
      )}
      {removeState.error && (
        <p
          role="alert"
          className="type-body-sm measure rounded-sm bg-error-subtle px-sm py-xs text-error"
        >
          {removeState.error}
        </p>
      )}
    </div>
  );
}
