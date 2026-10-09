import type { OrderStatus } from "@/lib/api";

export const ORDER_STATUS_LABELS: Record<OrderStatus, string> = {
  pending: "Pending",
  paid: "Paid",
  refunded: "Refunded",
  expired: "Expired",
};

const STATUS_CLASS_NAMES: Record<OrderStatus, string> = {
  pending: "bg-warning-subtle text-warning",
  paid: "bg-success-subtle text-success",
  refunded: "bg-paper-dim text-accent",
  expired: "bg-paper-dim text-meta-text",
};

// Not a chip: tertiary-pale chips are reserved for lesson status.
export function OrderStatusBadge({ status }: { status: OrderStatus }) {
  return (
    <span
      className={`type-label-caps inline-block whitespace-nowrap rounded-full px-sm py-xs ${STATUS_CLASS_NAMES[status]}`}
    >
      {ORDER_STATUS_LABELS[status]}
    </span>
  );
}
