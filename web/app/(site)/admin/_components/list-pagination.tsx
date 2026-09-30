import Link from "next/link";

/** Renders nothing when everything fits on one page. */
export function ListPagination({
  page,
  hasPrevious,
  hasNext,
  pageHref,
}: {
  page: number;
  hasPrevious: boolean;
  hasNext: boolean;
  /** Must keep the list's filters. */
  pageHref: (page: number) => string;
}) {
  if (!hasPrevious && !hasNext) return null;

  const linkClassName = "type-label-md text-primary underline";
  const disabledClassName = "type-label-md text-meta-text opacity-60";

  return (
    <nav
      aria-label="Pagination"
      className="mt-lg flex items-center justify-between gap-md"
    >
      {hasPrevious ? (
        <Link href={pageHref(page - 1)} className={linkClassName}>
          Previous
        </Link>
      ) : (
        <span className={disabledClassName}>Previous</span>
      )}
      <span className="type-body-sm text-meta-text">Page {page}</span>
      {hasNext ? (
        <Link href={pageHref(page + 1)} className={linkClassName}>
          Next
        </Link>
      ) : (
        <span className={disabledClassName}>Next</span>
      )}
    </nav>
  );
}
