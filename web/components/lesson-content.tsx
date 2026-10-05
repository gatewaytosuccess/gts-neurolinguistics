import type { ReactNode } from "react";

import { LessonSlides, LessonVideo } from "@/components/lesson-media";
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
  renderVideo = (video) => <LessonVideo {...video} />,
}: {
  lesson: LessonContentProps;
  tone: Tone;
  /** Replaces the plain `<video>`, e.g. to resume and save the learner's position. */
  renderVideo?: (video: { url: string; className: string }) => ReactNode;
}) {
  const color = colors[tone];

  if (!lesson.video_url && !lesson.slides_url && !lesson.body) {
    return <p className={`type-body-md ${color.empty}`}>No content yet</p>;
  }

  return (
    <div className="flex flex-col gap-xl">
      {lesson.video_url &&
        renderVideo({
          url: lesson.video_url,
          className: `aspect-video w-full rounded-xs ${color.frame}`,
        })}

      {lesson.slides_url && (
        <LessonSlides
          url={lesson.slides_url}
          title={`${lesson.title} slides`}
          frameClassName={`aspect-[4/3] w-full rounded-xs ${color.frame}`}
          linkClassName={`type-label-md mt-sm inline-block underline ${color.link}`}
        />
      )}

      {lesson.body && <Markdown tone={tone}>{lesson.body}</Markdown>}
    </div>
  );
}
