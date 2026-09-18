export function PlaceholderBadge({ show }: { show?: boolean }) {
  if (!show || process.env.NODE_ENV === "production") return null;

  return (
    <span className="type-label-caps inline-block rounded-xs border border-dashed border-warning bg-warning-subtle px-xs text-warning">
      Placeholder
    </span>
  );
}
