import Link from "next/link";

import type {
  CourseLesson,
  CourseModule,
  LessonKind,
  ViewerOutline,
} from "@/lib/api";
import { formatDuration } from "@/lib/format";

function twoDigits(n: number) {
  return String(n).padStart(2, "0");
}

type LessonState = {
  href: string | null;
  /** `undefined` unless the caller is enrolled. */
  completed?: boolean;
};

export function Curriculum({
  slug,
  modules,
  outline,
}: {
  slug: string;
  modules: CourseModule[];
  /** The caller's outline of the course; `null` when signed out or it couldn't be loaded. */
  outline: ViewerOutline | null;
}) {
  const outlineLessons = new Map(
    outline?.modules.flatMap((module) =>
      module.lessons.map((lesson) => [lesson.id, lesson]),
    ),
  );
  const enrolled = outline?.access === "enrolled";

  // The public course data is cached, so the outline may not have a lesson yet.
  function stateOf(lesson: CourseLesson): LessonState {
    const outlineLesson = outlineLessons.get(lesson.id);
    const open = outlineLesson ? !outlineLesson.locked : lesson.is_preview;
    return {
      href: open
        ? `/learn/${encodeURIComponent(slug)}/${encodeURIComponent(lesson.id)}`
        : null,
      completed: enrolled ? (outlineLesson?.completed ?? false) : undefined,
    };
  }

  return (
    <section aria-labelledby="curriculum-heading">
      <h2 id="curriculum-heading" className="type-headline-sm">
        Curriculum
      </h2>
      <ol className="mt-md">
        {modules.map((module, index) => (
          <ModuleItem
            key={module.id}
            module={module}
            number={index + 1}
            stateOf={stateOf}
          />
        ))}
      </ol>
    </section>
  );
}

function ModuleItem({
  module,
  number,
  stateOf,
}: {
  module: CourseModule;
  number: number;
  stateOf: (lesson: CourseLesson) => LessonState;
}) {
  return (
    <li className="border-t border-rule py-lg first:border-t-0 first:pt-0">
      <p className="type-label-caps text-accent">Module {twoDigits(number)}</p>
      <h3 className="type-label-lg mt-xs break-words">{module.title}</h3>
      {module.lessons.length > 0 && (
        <ol className="mt-sm">
          {module.lessons.map((lesson, index) => (
            <LessonItem
              key={lesson.id}
              lesson={lesson}
              number={`${number}.${index + 1}`}
              {...stateOf(lesson)}
            />
          ))}
        </ol>
      )}
    </li>
  );
}

function LessonItem({
  lesson,
  number,
  href,
  completed,
}: {
  lesson: CourseLesson;
  number: string;
} & LessonState) {
  return (
    <li className="flex items-baseline gap-sm py-xs">
      <span className="type-data-md min-w-[4ch] shrink-0 text-meta-text">
        {number}
      </span>
      <span className="type-body-md min-w-0 flex-1 break-words">
        {href ? (
          <Link
            href={href}
            className="text-primary underline hover:text-primary-strong"
          >
            {lesson.title}
          </Link>
        ) : (
          lesson.title
        )}
        {lesson.is_preview && (
          <span className="type-label-caps ml-sm whitespace-nowrap text-primary">
            Preview
          </span>
        )}
      </span>
      <span className="flex shrink-0 items-center gap-sm self-center text-meta-text">
        {lesson.kinds.map((kind) => (
          <KindGlyph key={kind} kind={kind} />
        ))}
        {/* Rendered empty too, so glyphs line up across rows. */}
        <span className="type-caption min-w-[6ch] text-right tabular-nums">
          {lesson.duration_seconds !== null &&
            formatDuration(lesson.duration_seconds)}
        </span>
        {completed !== undefined && <CompletedGlyph completed={completed} />}
      </span>
    </li>
  );
}

// Rendered empty too, so durations line up across rows.
function CompletedGlyph({ completed }: { completed: boolean }) {
  if (!completed) return <span aria-hidden className="w-[16px]" />;

  return (
    <svg
      role="img"
      aria-label="Completed"
      viewBox="0 0 16 16"
      width={16}
      height={16}
      fill="none"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      className="text-success"
    >
      <title>Completed</title>
      <circle cx="8" cy="8" r="6.5" fill="currentColor" />
      <path d="M5 8.25l2 2 4-4.25" stroke="var(--color-paper)" />
    </svg>
  );
}

const KIND_LABELS: Record<LessonKind, string> = {
  video: "Video",
  slides: "Slides",
  text: "Text",
};

function KindGlyph({ kind }: { kind: LessonKind }) {
  return (
    <svg
      role="img"
      aria-label={KIND_LABELS[kind]}
      viewBox="0 0 16 16"
      width={16}
      height={16}
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <title>{KIND_LABELS[kind]}</title>
      {kind === "video" && <path d="M5 3.5v9l7.5-4.5z" fill="currentColor" />}
      {kind === "slides" && (
        <>
          <rect x="2" y="2.5" width="12" height="8.5" rx="1" />
          <path d="M8 11v2.5M5.5 13.5h5" />
        </>
      )}
      {kind === "text" && <path d="M3 4h10M3 7h10M3 10h10M3 13h6" />}
    </svg>
  );
}
