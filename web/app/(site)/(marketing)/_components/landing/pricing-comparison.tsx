import Link from "next/link";

import { PlaceholderBadge } from "./placeholder-badge";
import { PriceDisplay } from "./price-display";
import { RecurringPrice } from "./recurring-price";
import { SectionHeading } from "./section-heading";
import type { PricingTier } from "./types";

export function PricingComparison({ tiers }: { tiers: PricingTier[] }) {
  return (
    <section
      aria-labelledby="pricing-heading"
      className="mx-auto max-w-[1200px] px-md py-2xl sm:px-margin lg:py-3xl"
    >
      <SectionHeading
        id="pricing-heading"
        eyebrow="Ways to enroll"
        title="Buy the course you need, or take every one of them."
      />

      <ul className="mt-xl grid gap-gutter lg:grid-cols-3">
        {tiers.map((tier) => (
          <li key={tier.name}>
            <TierColumn tier={tier} />
          </li>
        ))}
      </ul>
    </section>
  );
}

function TierColumn({ tier }: { tier: PricingTier }) {
  return (
    <article
      className={`flex h-full flex-col rounded-lg border bg-paper-raised p-lg ${
        tier.highlighted ? "border-primary" : "border-rule"
      }`}
    >
      {tier.highlighted && (
        <p className="type-label-caps mb-sm text-primary">Recommended</p>
      )}
      <div className="flex flex-wrap items-center gap-sm">
        <h3 className="type-headline-sm">{tier.name}</h3>
        <PlaceholderBadge show={tier.placeholder} />
      </div>
      <p className="type-body-md mt-sm">{tier.summary}</p>

      <div className="mt-lg border-t border-rule pt-lg">
        {tier.billing === "recurring" ? (
          <RecurringPrice monthly={tier.monthly} annual={tier.annual} />
        ) : (
          <PriceDisplay price={tier.price} />
        )}
      </div>

      <ul className="mt-lg flex-1">
        {tier.features.map((feature) => (
          <li
            key={feature}
            className="type-body-sm border-t border-rule py-sm first:border-t-0"
          >
            {feature}
          </li>
        ))}
      </ul>

      <div className="mt-lg">
        <Link
          href={tier.cta.href}
          className={`w-full ${tier.highlighted ? "button-primary" : "button-secondary"}`}
        >
          {tier.cta.label}
        </Link>
      </div>
    </article>
  );
}
