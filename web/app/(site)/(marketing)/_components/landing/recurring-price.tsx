"use client";

import { useState } from "react";

import { PriceDisplay } from "./price-display";
import type { Price } from "./types";

type Interval = "monthly" | "annual";

const intervals: Array<{ value: Interval; label: string }> = [
  { value: "monthly", label: "Monthly" },
  { value: "annual", label: "Annual" },
];

export function RecurringPrice({
  monthly,
  annual,
}: {
  monthly: Price;
  annual: Price;
}) {
  const [interval, setBillingInterval] = useState<Interval>("monthly");

  return (
    <div>
      <div
        role="group"
        aria-label="Billing interval"
        className="mb-md inline-flex rounded-sm border border-border-strong p-xs"
      >
        {intervals.map((option) => (
          <button
            key={option.value}
            type="button"
            aria-pressed={interval === option.value}
            onClick={() => setBillingInterval(option.value)}
            className="type-label-md rounded-xs px-sm py-xs text-meta-text aria-pressed:bg-primary-pale aria-pressed:text-primary-strong"
          >
            {option.label}
          </button>
        ))}
      </div>

      <PriceDisplay price={interval === "monthly" ? monthly : annual} />
    </div>
  );
}
