import Link from "next/link";

import { formatPrice } from "./format";
import { PlaceholderBadge } from "./placeholder-badge";
import { SectionHeading } from "./section-heading";
import type { CoursePreview as Course } from "./types";

export function CoursePreview({ courses }: { courses: Course[] }) {
  return (
    <section
      aria-labelledby="courses-heading"
      className="mx-auto max-w-[1200px] px-md py-2xl sm:px-margin lg:py-3xl"
    >
      <SectionHeading
        id="courses-heading"
        eyebrow="The catalog"
        title="Start with one course, or work through them in order."
      />

      <ul className="mt-xl grid gap-gutter md:grid-cols-3">
        {courses.map((course) => (
          <li key={course.slug}>
            <CourseCard course={course} />
          </li>
        ))}
      </ul>

      <div className="mt-xl">
        <Link href="/courses" className="button-secondary">
          Browse all courses
        </Link>
      </div>
    </section>
  );
}

function CourseCard({ course }: { course: Course }) {
  return (
    <article className="flex h-full flex-col rounded-lg bg-paper-raised p-lg">
      {/* Thumbnail frame until course imagery exists. */}
      <div aria-hidden className="h-[220px] rounded-xs bg-paper-dim" />

      <div className="mt-md">
        <PlaceholderBadge show={course.placeholder} />
      </div>
      <h3 className="type-headline-sm mt-sm">{course.title}</h3>
      <p className="type-body-md mt-sm flex-1">{course.description}</p>

      <div className="mt-lg flex items-baseline justify-between gap-md border-t border-rule pt-md">
        <span className="type-data-md">{formatPrice(course.priceCents)}</span>
        <span className="type-data-md text-meta-text">
          <span aria-hidden className="text-tertiary-strong">
            ★{" "}
          </span>
          {course.rating.toFixed(1)}
          <span className="type-caption">
            {" "}
            ({course.ratingCount.toLocaleString("en-US")} ratings)
          </span>
        </span>
      </div>
    </article>
  );
}
