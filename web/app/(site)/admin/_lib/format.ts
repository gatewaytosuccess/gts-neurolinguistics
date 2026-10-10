const dateFormat = new Intl.DateTimeFormat("en-US", {
  year: "numeric",
  month: "short",
  day: "numeric",
});

/** "Sep 30, 2026", from an ISO timestamp. */
export function formatDate(iso: string) {
  return dateFormat.format(new Date(iso));
}
