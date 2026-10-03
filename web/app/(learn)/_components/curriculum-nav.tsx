"use client";

import Link from "next/link";
import { useId } from "react";

import type { OutlineLesson, OutlineModule } from "@/lib/api";
import { formatDuration } from "@/lib/format";

function twoDigits(n: number) {
  return String(n).padStart(2, "0");
}

export function CurriculumNav({
  slug,
  modules,
  currentLessonId,
  expanded,
  onToggle,
  onNavigate,
}: {
  slug: string;
  modules: OutlineModule[];
  currentLessonId: string | undefined;
  /** Ids of the open modules. */
  expanded: ReadonlySet<string>;
  onToggle: (moduleId: string) => void;
  onNavigate?: () => void;
}) {
  return (
    <nav aria-label="Curriculum">
      <ol className="flex flex-col gap-xs">
        {modules.map((module) => (
          <ModuleItem
            key={module.id}
            slug={slug}
            module={module}
            currentLessonId={currentLessonId}
            open={expanded.has(module.id)}
            onToggle={() => onToggle(module.id)}
            onNavigate={onNavigate}
          />
        ))}
      </ol>
    </nav>
  );
}

function ModuleItem({
  slug,
  module,
  currentLessonId,
  open,
  onToggle,
  onNavigate,
}: {
  slug: string;
  module: OutlineModule;
  currentLessonId: string | undefined;
  open: boolean;
  onToggle: () => void;
  onNavigate?: () => void;
}) {
  const lessonsId = useId();
  const label = (
    <span className="min-w-0 flex-1">
      <span className="type-label-caps block text-dark-on-surface-meta">
        Module {twoDigits(module.position)}
      </span>
      <span className="type-label-md mt-xs block break-words">
        {module.title}
      </span>
    </span>
  );

  if (module.lessons.length === 0) {
    return (
      <li className="flex px-sm py-sm text-dark-on-surface-meta">{label}</li>
    );
  }

  return (
    <li>
      <button
        type="button"
        aria-expanded={open}
        aria-controls={lessonsId}
        onClick={onToggle}
        className="flex w-full items-start gap-sm rounded-sm px-sm py-sm text-left hover:bg-dark-surface"
      >
        {label}
        <Chevron open={open} />
      </button>
      <ol id={lessonsId} hidden={!open} className="pb-sm">
        {module.lessons.map((lesson) => (
          <LessonItem
            key={lesson.id}
            slug={slug}
            lesson={lesson}
            current={lesson.id === currentLessonId}
            onNavigate={onNavigate}
          />
        ))}
      </ol>
    </li>
  );
}

function LessonItem({
  slug,
  lesson,
  current,
  onNavigate,
}: {
  slug: string;
  lesson: OutlineLesson;
  current: boolean;
  onNavigate?: () => void;
}) {
  return (
    <li>
      <Link
        href={`/learn/${encodeURIComponent(slug)}/${encodeURIComponent(lesson.id)}`}
        aria-current={current ? "page" : undefined}
        onClick={onNavigate}
        className={`flex items-start gap-sm rounded-sm border-l-2 py-xs pr-sm pl-[calc(var(--spacing-sm)-2px)] ${
          current
            ? "border-dark-tertiary bg-dark-surface-overlay text-dark-on-surface"
            : "border-transparent hover:bg-dark-surface"
        } ${lesson.locked && !current ? "text-dark-on-surface-meta" : ""}`}
      >
        <StatusGlyph lesson={lesson} />
        <span className="type-body-sm min-w-0 flex-1 break-words">
          {lesson.title}
        </span>
        {lesson.duration_seconds !== null && (
          <span className="type-caption shrink-0 pt-[2px] text-dark-on-surface-meta tabular-nums">
            {formatDuration(lesson.duration_seconds)}
          </span>
        )}
      </Link>
    </li>
  );
}

// Fixed box so titles line up whichever glyph a row has.
function StatusGlyph({ lesson }: { lesson: OutlineLesson }) {
  const shared = {
    viewBox: "0 0 16 16",
    width: 16,
    height: 16,
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.5,
    strokeLinecap: "round",
    strokeLinejoin: "round",
    className: "mt-[3px] shrink-0",
  } as const;

  if (lesson.completed) {
    return (
      <svg
        {...shared}
        role="img"
        aria-label="Completed"
        className={`${shared.className} text-dark-success`}
      >
        <title>Completed</title>
        <circle cx="8" cy="8" r="6.5" fill="currentColor" stroke="none" />
        <path d="M5 8.25l2 2 4-4.25" stroke="var(--color-dark-bg)" />
      </svg>
    );
  }
  if (lesson.locked) {
    return (
      <svg {...shared} role="img" aria-label="Locked">
        <title>Locked</title>
        <rect x="3.5" y="7" width="9" height="6.5" rx="1" />
        <path d="M5.5 7V5a2.5 2.5 0 015 0v2" />
      </svg>
    );
  }
  return (
    <svg
      {...shared}
      aria-hidden
      className={`${shared.className} text-dark-border-strong`}
    >
      <circle cx="8" cy="8" r="6" />
    </svg>
  );
}

function Chevron({ open }: { open: boolean }) {
  return (
    <svg
      viewBox="0 0 16 16"
      width={16}
      height={16}
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
      className={`mt-[3px] shrink-0 text-dark-on-surface-meta transition-transform duration-150 ${
        open ? "rotate-180" : ""
      }`}
    >
      <path d="M4 6l4 4 4-4" />
    </svg>
  );
}
