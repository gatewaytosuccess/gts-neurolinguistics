import Link from "next/link";

import { CourseComplete } from "./course-complete";
import { MarkComplete } from "./mark-complete";

const linkClass =
  "type-label-lg text-dark-primary hover:text-dark-primary-strong";

export function LessonFooter({
  slug,
  lessonId,
  previousLessonId,
  nextLessonId,
}: {
  slug: string;
  lessonId: string;
  previousLessonId: string | null;
  nextLessonId: string | null;
}) {
  const lessonHref = (id: string) =>
    `/learn/${encodeURIComponent(slug)}/${encodeURIComponent(id)}`;

  return (
    <footer className="mt-2xl border-t border-dark-rule pt-lg">
      <div className="grid grid-cols-[1fr_auto_1fr] items-start gap-md">
        <span>
          {previousLessonId && (
            <Link href={lessonHref(previousLessonId)} className={linkClass}>
              &larr; Previous
            </Link>
          )}
        </span>
        {/* Holds the middle column when there's no button. */}
        <span>
          <MarkComplete lessonId={lessonId} />
        </span>
        <span className="justify-self-end">
          {nextLessonId ? (
            <Link href={lessonHref(nextLessonId)} className={linkClass}>
              Next &rarr;
            </Link>
          ) : (
            <Link
              href={`/courses/${encodeURIComponent(slug)}`}
              className={linkClass}
            >
              Back to course
            </Link>
          )}
        </span>
      </div>
      {!nextLessonId && <CourseComplete slug={slug} />}
    </footer>
  );
}
