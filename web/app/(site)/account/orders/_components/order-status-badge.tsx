import type { PurchasedOrder } from "@/lib/api";

type Status = PurchasedOrder["status"];

const STATUS_LABELS: Record<Status, string> = {
  paid: "Paid",
  refunded: "Refunded",
};

const STATUS_CLASS_NAMES: Record<Status, string> = {
  paid: "bg-success-subtle text-success",
  refunded: "bg-paper-dim text-accent",
};

// Not a chip: tertiary-pale chips are reserved for lesson status.
export function OrderStatusBadge({ status }: { status: Status }) {
  return (
    <span
      className={`type-label-caps inline-block whitespace-nowrap rounded-full px-sm py-xs ${STATUS_CLASS_NAMES[status]}`}
    >
      {STATUS_LABELS[status]}
    </span>
  );
}
