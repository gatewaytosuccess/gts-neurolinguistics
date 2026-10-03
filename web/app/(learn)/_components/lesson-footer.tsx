import Link from "next/link";

const linkClass =
  "type-label-lg text-dark-primary hover:text-dark-primary-strong";

export function LessonFooter({
  slug,
  previousLessonId,
  nextLessonId,
}: {
  slug: string;
  previousLessonId: string | null;
  nextLessonId: string | null;
}) {
  const lessonHref = (id: string) =>
    `/learn/${encodeURIComponent(slug)}/${encodeURIComponent(id)}`;

  return (
    <nav
      aria-label="Lessons"
      className="mt-2xl flex items-center justify-between gap-md border-t border-dark-rule pt-lg"
    >
      {previousLessonId ? (
        <Link href={lessonHref(previousLessonId)} className={linkClass}>
          &larr; Previous
        </Link>
      ) : (
        <span />
      )}
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
    </nav>
  );
}
