import type { CourseStatus } from "@/lib/api";

export const STATUS_LABELS: Record<CourseStatus, string> = {
  draft: "Draft",
  published: "Published",
};

// Not a chip: tertiary-pale chips are reserved for lesson status.
export function StatusBadge({ status }: { status: CourseStatus }) {
  return (
    <span
      className={`type-label-caps inline-block whitespace-nowrap rounded-full px-sm py-xs ${
        status === "published"
          ? "bg-success-subtle text-success"
          : "bg-paper-dim text-accent"
      }`}
    >
      {STATUS_LABELS[status]}
    </span>
  );
}
