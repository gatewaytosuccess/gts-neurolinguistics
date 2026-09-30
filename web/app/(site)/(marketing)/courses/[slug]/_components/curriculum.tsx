import type { CourseLesson, CourseModule, LessonKind } from "@/lib/api";
import { formatDuration } from "@/lib/format";

function twoDigits(n: number) {
  return String(n).padStart(2, "0");
}

export function Curriculum({ modules }: { modules: CourseModule[] }) {
  return (
    <section aria-labelledby="curriculum-heading">
      <h2 id="curriculum-heading" className="type-headline-sm">
        Curriculum
      </h2>
      <ol className="mt-md">
        {modules.map((module, index) => (
          <ModuleItem key={module.id} module={module} number={index + 1} />
        ))}
      </ol>
    </section>
  );
}

function ModuleItem({
  module,
  number,
}: {
  module: CourseModule;
  number: number;
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
            />
          ))}
        </ol>
      )}
    </li>
  );
}

// Preview lessons are plain rows, not links, until the lesson viewer exists.
function LessonItem({
  lesson,
  number,
}: {
  lesson: CourseLesson;
  number: string;
}) {
  return (
    <li className="flex items-baseline gap-sm py-xs">
      <span className="type-data-md min-w-[4ch] shrink-0 text-meta-text">
        {number}
      </span>
      <span className="type-body-md min-w-0 flex-1 break-words">
        {lesson.title}
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
      </span>
    </li>
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
