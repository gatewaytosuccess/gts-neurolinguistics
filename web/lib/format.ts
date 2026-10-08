const usd = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
});

export function formatPrice(cents: number) {
  return usd.format(cents / 100);
}

/** "45 sec", "12 min", or "1 h 5 min". */
export function formatDuration(seconds: number) {
  if (seconds < 60) return `${seconds} sec`;
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest ? `${hours} h ${rest} min` : `${hours} h`;
}

/** "about 4 h", or "about 40 min" under an hour. */
export function formatApproximateDuration(seconds: number) {
  const minutes = Math.max(1, Math.round(seconds / 60));
  if (minutes < 60) return `about ${minutes} min`;
  return `about ${Math.round(minutes / 60)} h`;
}

const monthYear = new Intl.DateTimeFormat("en-US", {
  month: "long",
  year: "numeric",
  timeZone: "UTC",
});

/** "March 2026", from an ISO timestamp. */
export function formatMonthYear(iso: string) {
  return monthYear.format(new Date(iso));
}

const longDate = new Intl.DateTimeFormat("en-US", {
  month: "long",
  day: "numeric",
  year: "numeric",
  timeZone: "UTC",
});

/** "March 4, 2026", from an ISO timestamp. */
export function formatDate(iso: string) {
  return longDate.format(new Date(iso));
}
