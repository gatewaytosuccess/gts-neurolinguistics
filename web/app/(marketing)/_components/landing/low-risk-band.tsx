import { PlaceholderBadge } from "./placeholder-badge";
import type { LowRiskContent } from "./types";

export function LowRiskBand({ content }: { content: LowRiskContent }) {
  return (
    <section aria-label="Cancel anytime" className="bg-paper-dim">
      <div className="mx-auto max-w-[1200px] px-md py-xl sm:px-margin lg:py-2xl">
        <p className="type-headline-sm measure">{content.line}</p>
        <div className="mt-sm">
          <PlaceholderBadge show={content.placeholder} />
        </div>
      </div>
    </section>
  );
}
