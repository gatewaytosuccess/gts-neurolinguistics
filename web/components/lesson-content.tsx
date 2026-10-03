import { Markdown, type Tone } from "@/components/markdown";

export type LessonContentProps = {
  title: string;
  /** Markdown; blank when the lesson has no text. */
  body: string;
  /** Blank when the lesson has no video. */
  video_url: string;
  /** Blank when the lesson has no slides. */
  slides_url: string;
};

const colors = {
  light: {
    frame: "bg-paper-dim",
    link: "text-tertiary-strong hover:text-primary",
    empty: "text-meta-text",
  },
  dark: {
    frame: "bg-dark-surface",
    link: "text-dark-primary hover:text-dark-primary-strong",
    empty: "text-dark-on-surface-meta",
  },
} satisfies Record<Tone, Record<string, string>>;

/** Video, then slides, then text, each only when the lesson has it. */
export function LessonContent({
  lesson,
  tone,
}: {
  lesson: LessonContentProps;
  tone: Tone;
}) {
  const color = colors[tone];

  if (!lesson.video_url && !lesson.slides_url && !lesson.body) {
    return <p className={`type-body-md ${color.empty}`}>No content yet</p>;
  }

  return (
    <div className="flex flex-col gap-xl">
      {lesson.video_url && (
        <video
          src={lesson.video_url}
          controls
          preload="metadata"
          className={`aspect-video w-full rounded-xs ${color.frame}`}
        />
      )}

      {lesson.slides_url && (
        <div>
          <iframe
            src={lesson.slides_url}
            title={`${lesson.title} slides`}
            className={`aspect-[4/3] w-full rounded-xs ${color.frame}`}
          />
          {/* Some browsers, most phones among them, can't show a PDF inline. */}
          <a
            href={lesson.slides_url}
            target="_blank"
            rel="noreferrer"
            className={`type-label-md mt-sm inline-block underline ${color.link}`}
          >
            Download the slides (PDF)
          </a>
        </div>
      )}

      {lesson.body && <Markdown tone={tone}>{lesson.body}</Markdown>}
    </div>
  );
}
