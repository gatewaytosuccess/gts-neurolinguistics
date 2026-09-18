/*
 * Content shapes for the landing page. Anything flagged `placeholder` is
 * invented copy that must be replaced before launch, and shows a dev-only badge.
 */

type Flaggable = { placeholder?: true };

export type HeroContent = {
  eyebrow: string;
  headline: string;
  body: string;
};

export type Stat = Flaggable & {
  value: string;
  label: string;
};

export type CoursePreview = Flaggable & {
  slug: string;
  title: string;
  description: string;
  priceCents: number;
  rating: number;
  ratingCount: number;
};

export type Instructor = Flaggable & {
  name: string;
  title: string;
  bio: string[];
  credentials: string[];
};

export type Testimonial = Flaggable & {
  quote: string;
  name: string;
  context: string;
};

export type Price = {
  amountCents: number;
  period?: string;
  note?: string;
};

export type PricingTier = Flaggable & {
  name: string;
  summary: string;
  features: string[];
  cta: { label: string; href: string };
  highlighted?: boolean;
} & (
    | { billing: "one-time"; price: Price }
    | { billing: "recurring"; monthly: Price; annual: Price }
  );

export type LowRiskContent = Flaggable & {
  line: string;
};

export type LandingContent = {
  hero: HeroContent;
  stats: Stat[];
  courses: CoursePreview[];
  instructor: Instructor;
  testimonials: [Testimonial, Testimonial, Testimonial];
  pricing: PricingTier[];
  lowRisk: LowRiskContent;
};
