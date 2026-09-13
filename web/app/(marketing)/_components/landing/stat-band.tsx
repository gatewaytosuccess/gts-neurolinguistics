import { PlaceholderBadge } from "./placeholder-badge";
import type { Stat } from "./types";

export function StatBand({ stats }: { stats: Stat[] }) {
  return (
    <section aria-label="By the numbers" className="bg-primary">
      <dl className="mx-auto grid max-w-[1200px] gap-xl px-md py-xl sm:px-margin md:grid-cols-3 md:gap-gutter lg:py-2xl">
        {stats.map((stat) => (
          <div key={stat.label} className="flex flex-col">
            {/* Label first for screen readers, value first on screen. */}
            <dt className="type-label-caps order-2 mt-sm flex flex-wrap items-center gap-sm text-primary-subtle">
              {stat.label}
              <PlaceholderBadge show={stat.placeholder} />
            </dt>
            <dd className="type-headline-lg order-1 text-primary-pale lg:type-display">
              {stat.value}
            </dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
