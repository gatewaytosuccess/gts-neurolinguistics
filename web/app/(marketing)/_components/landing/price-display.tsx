import { formatPrice } from "./format";
import type { Price } from "./types";

export function PriceDisplay({ price }: { price: Price }) {
  return (
    <div>
      <p className="flex items-baseline gap-xs">
        <span className="type-headline-sm">{formatPrice(price.amountCents)}</span>
        {price.period && (
          <span className="type-body-sm text-meta-text">/ {price.period}</span>
        )}
      </p>
      {/* Reserve the line so columns stay aligned when a price has no note. */}
      <p className="type-caption mt-xs min-h-[1.45em] text-meta-text">
        {price.note}
      </p>
    </div>
  );
}
