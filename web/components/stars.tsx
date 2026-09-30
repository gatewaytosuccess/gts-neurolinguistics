export function Stars({ rating, label }: { rating: number; label: string }) {
  return (
    <span
      role="img"
      aria-label={label}
      className="type-body-md tracking-[0.1em] whitespace-nowrap"
    >
      <span aria-hidden className="text-tertiary-strong">
        {"★".repeat(rating)}
      </span>
      <span aria-hidden className="text-border-strong">
        {"★".repeat(5 - rating)}
      </span>
    </span>
  );
}
