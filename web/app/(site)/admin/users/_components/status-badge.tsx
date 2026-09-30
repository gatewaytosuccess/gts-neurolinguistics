import type { AccountStatus } from "@/lib/api";

export const STATUS_LABELS: Record<AccountStatus, string> = {
  active: "Active",
  suspended: "Suspended",
  deleted: "Deleted",
};

const STATUS_CLASS_NAMES: Record<AccountStatus, string> = {
  active: "bg-success-subtle text-success",
  suspended: "bg-warning-subtle text-warning",
  deleted: "bg-paper-dim text-accent",
};

// Not a chip: tertiary-pale chips are reserved for lesson status.
export function StatusBadge({ status }: { status: AccountStatus }) {
  return (
    <span
      className={`type-label-caps inline-block whitespace-nowrap rounded-full px-sm py-xs ${STATUS_CLASS_NAMES[status]}`}
    >
      {STATUS_LABELS[status]}
    </span>
  );
}
