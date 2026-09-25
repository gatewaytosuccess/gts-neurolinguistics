"use client";

import { useActionState, useRef, useState, type ReactNode } from "react";

import { Markdown } from "@/components/markdown";
import type { LessonFileKind } from "@/lib/api";

import { splitDuration, type LessonEditorState } from "../_lib/lesson-editor";
import type { UploadResult, UploadTicket } from "../_lib/uploads";
import { LessonFile, readVideoDuration } from "./lesson-file";
import { PublishProblems } from "./publish-problems";

const fieldClassName =
  "type-body-md mt-xs w-full rounded-sm border bg-paper-raised px-sm py-sm text-accent-strong placeholder:text-meta-text";

/** The hint's id, plus the error's while there is one. */
function describedBy(id: string, errors?: string[]) {
  return errors ? `${id}-hint ${id}-error` : `${id}-hint`;
}

function borderClassName(errors?: string[]) {
  return errors ? "border-error" : "border-border-strong";
}

export function LessonEditorForm({
  action,
  initialState,
  files,
}: {
  action: (
    state: LessonEditorState,
    formData: FormData,
  ) => Promise<LessonEditorState>;
  initialState: LessonEditorState;
  files: {
    /** Blank when the lesson has no video. */
    videoUrl: string;
    /** Blank when the lesson has no slides. */
    slidesUrl: string;
    requestUpload: (kind: LessonFileKind) => Promise<UploadTicket>;
    save: (
      kind: LessonFileKind,
      key: string,
      durationSeconds?: number | null,
    ) => Promise<UploadResult>;
  };
}) {
  const [state, formAction, pending] = useActionState(action, initialState);
  const { values, errors } = state;

  // Controlled so the preview and the video upload can reach them; resynced
  // when a save returns new values.
  const [body, setBody] = useState(values.body);
  const [duration, setDuration] = useState({
    minutes: values.minutes,
    seconds: values.seconds,
  });
  const [syncedState, setSyncedState] = useState(state);
  if (syncedState !== state) {
    setSyncedState(state);
    setBody(state.values.body);
    setDuration({
      minutes: state.values.minutes,
      seconds: state.values.seconds,
    });
  }
  const [previewing, setPreviewing] = useState(false);

  // Read from the chosen video, then saved with its key.
  const videoDuration = useRef<Promise<number | null>>(Promise.resolve(null));

  return (
    // Fields read their defaults from `state`: React resets the form after every submission.
    <form action={formAction} className="mt-xl flex flex-col gap-2xl">
      {errors.form && (
        <p
          role="alert"
          className="type-body-sm measure rounded-sm bg-error-subtle px-sm py-sm text-error"
        >
          {errors.form.join(" ")}
        </p>
      )}
      {state.problems && (
        <PublishProblems refused="edit" problems={state.problems} />
      )}

      <section
        aria-labelledby="lesson-details-heading"
        className="measure flex flex-col gap-lg"
      >
        <h2 id="lesson-details-heading" className="type-headline-sm">
          Details
        </h2>

        <div>
          <label htmlFor="lesson-title" className="type-label-md block">
            Title
          </label>
          <input
            id="lesson-title"
            name="title"
            type="text"
            required
            maxLength={255}
            defaultValue={values.title}
            className={`${fieldClassName} ${borderClassName(errors.title)}`}
            {...(errors.title && {
              "aria-invalid": true,
              "aria-describedby": "lesson-title-error",
            })}
          />
          <FieldErrors id="lesson-title-error" errors={errors.title} />
        </div>

        <fieldset
          aria-describedby={describedBy("lesson-duration", errors.duration)}
        >
          <legend className="type-label-md">Duration</legend>
          <div className="flex flex-wrap gap-md">
            <DurationPart
              name="minutes"
              label="Minutes"
              value={duration.minutes}
              onChange={(minutes) => setDuration({ ...duration, minutes })}
              errors={errors.duration}
            />
            <DurationPart
              name="seconds"
              label="Seconds"
              value={duration.seconds}
              onChange={(seconds) => setDuration({ ...duration, seconds })}
              errors={errors.duration}
            />
          </div>
          <p
            id="lesson-duration-hint"
            className="type-caption mt-xs text-meta-text"
          >
            Filled in when a video is uploaded. Leave both blank if you
            don&rsquo;t know it yet.
          </p>
          <FieldErrors id="lesson-duration-error" errors={errors.duration} />
        </fieldset>

        <div className="flex items-start gap-sm">
          <input
            id="lesson-is-preview"
            name="is_preview"
            type="checkbox"
            defaultChecked={values.isPreview}
            aria-describedby="lesson-is-preview-hint"
            className="mt-xs size-4 accent-primary"
          />
          <div>
            <label htmlFor="lesson-is-preview" className="type-label-md">
              Preview lesson
            </label>
            <p
              id="lesson-is-preview-hint"
              className="type-caption text-meta-text"
            >
              Anyone can open it without being enrolled, to sample the course.
            </p>
          </div>
        </div>
      </section>

      <LessonFile
        kind="video"
        url={files.videoUrl}
        requestUpload={() => files.requestUpload("video")}
        onChoose={(file) => {
          videoDuration.current = readVideoDuration(file).then((seconds) => {
            if (seconds !== null) setDuration(splitDuration(seconds));
            return seconds;
          });
        }}
        save={async (key) =>
          files.save("video", key, (await videoDuration.current) ?? undefined)
        }
        remove={async () => {
          const result = await files.save("video", "", null);
          if (!result.error) setDuration(splitDuration(null));
          return result;
        }}
      />

      <LessonFile
        kind="slides"
        url={files.slidesUrl}
        requestUpload={() => files.requestUpload("slides")}
        save={(key) => files.save("slides", key)}
        remove={() => files.save("slides", "")}
      />

      <section aria-labelledby="lesson-body-heading" className="measure">
        <div className="flex flex-wrap items-end justify-between gap-md">
          <h2 id="lesson-body-heading" className="type-headline-sm">
            Body
          </h2>
          <div
            role="group"
            aria-label="Body view"
            className="flex rounded-sm border border-border-strong"
          >
            <ToggleButton
              pressed={!previewing}
              onClick={() => setPreviewing(false)}
            >
              Write
            </ToggleButton>
            <ToggleButton
              pressed={previewing}
              onClick={() => setPreviewing(true)}
            >
              Preview
            </ToggleButton>
          </div>
        </div>

        <label htmlFor="lesson-body" className="sr-only">
          Body
        </label>
        <textarea
          id="lesson-body"
          name="body"
          rows={16}
          // Hidden, not unmounted, while previewing: it still submits with the form.
          hidden={previewing}
          value={body}
          onChange={(event) => setBody(event.target.value)}
          aria-describedby={describedBy("lesson-body", errors.body)}
          className={`${fieldClassName} mt-md font-mono ${borderClassName(errors.body)}`}
        />
        {previewing && (
          <div className="mt-md min-h-[200px] rounded-sm border border-rule bg-paper-raised p-md">
            {body.trim() ? (
              <Markdown>{body}</Markdown>
            ) : (
              <p className="type-body-md text-meta-text">Nothing to preview.</p>
            )}
          </div>
        )}
        <p id="lesson-body-hint" className="type-caption mt-xs text-meta-text">
          Markdown. HTML is shown as text, not rendered.
        </p>
        <FieldErrors id="lesson-body-error" errors={errors.body} />
      </section>

      <div className="flex flex-wrap items-center gap-md">
        <button
          type="submit"
          disabled={pending}
          className="button-primary disabled:cursor-wait disabled:opacity-60"
        >
          {pending ? "Saving…" : "Save lesson"}
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

function DurationPart({
  name,
  label,
  value,
  onChange,
  errors,
}: {
  name: "minutes" | "seconds";
  label: string;
  value: string;
  onChange: (value: string) => void;
  errors?: string[];
}) {
  const id = `lesson-duration-${name}`;
  return (
    <div className="w-[120px]">
      <label htmlFor={id} className="type-body-sm mt-xs block text-meta-text">
        {label}
      </label>
      <input
        id={id}
        name={name}
        type="text"
        inputMode="numeric"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        {...(errors && { "aria-invalid": true })}
        className={`${fieldClassName} type-data-md ${borderClassName(errors)}`}
      />
    </div>
  );
}

function ToggleButton({
  pressed,
  onClick,
  children,
}: {
  pressed: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      aria-pressed={pressed}
      onClick={onClick}
      className={`type-label-md px-sm py-xs ${
        pressed
          ? "bg-primary text-paper-raised"
          : "bg-paper-raised text-primary hover:bg-primary-pale"
      }`}
    >
      {children}
    </button>
  );
}

function FieldErrors({ id, errors }: { id: string; errors?: string[] }) {
  if (!errors) return null;
  return (
    <p id={id} className="type-body-sm mt-xs text-error">
      {errors.join(" ")}
    </p>
  );
}
