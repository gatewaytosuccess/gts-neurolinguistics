import { PlaceholderBadge } from "./placeholder-badge";
import { SectionHeading } from "./section-heading";
import type { Testimonial } from "./types";

export function Testimonials({
  testimonials: [featured, ...rest],
}: {
  testimonials: [Testimonial, Testimonial, Testimonial];
}) {
  return (
    <section
      aria-labelledby="testimonials-heading"
      className="mx-auto max-w-[1200px] px-md py-2xl sm:px-margin lg:py-3xl"
    >
      <SectionHeading
        id="testimonials-heading"
        eyebrow="From learners"
        title="What people say after the first module."
      />

      <div className="mt-xl grid gap-gutter lg:grid-cols-3">
        <figure className="flex flex-col justify-between gap-xl rounded-lg bg-primary p-lg lg:col-span-2 lg:row-span-2 lg:p-xl">
          <blockquote className="type-quote measure text-primary-pale">
            “{featured.quote}”
          </blockquote>
          <Byline testimonial={featured} tone="navy" />
        </figure>

        {rest.map((testimonial) => (
          <figure
            key={testimonial.name}
            className="flex flex-col justify-between gap-lg rounded-lg bg-paper-raised p-lg"
          >
            <blockquote className="type-quote">
              “{testimonial.quote}”
            </blockquote>
            <Byline testimonial={testimonial} tone="paper" />
          </figure>
        ))}
      </div>
    </section>
  );
}

function Byline({
  testimonial,
  tone,
}: {
  testimonial: Testimonial;
  tone: "navy" | "paper";
}) {
  return (
    <figcaption
      className={`type-caption flex flex-wrap items-center gap-sm ${
        tone === "navy" ? "text-primary-muted" : "text-meta-text"
      }`}
    >
      <span>
        {testimonial.name}, {testimonial.context}
      </span>
      <PlaceholderBadge show={testimonial.placeholder} />
    </figcaption>
  );
}
