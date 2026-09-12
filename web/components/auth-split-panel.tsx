import type { ReactNode } from "react";
import Link from "next/link";

/*
 * The frame both account pages sit in. Nothing is centered: DESIGN.md is
 * explicit that a centered hero is the fastest way for this to read as a
 * generic SaaS template rather than a course catalog.
 */
export function AuthSplitPanel({
  eyebrow,
  headline,
  children,
}: {
  eyebrow: string;
  headline: string;
  children: ReactNode;
}) {
  return (
    <main className="flex flex-1 flex-col lg:flex-row">
      <section className="bg-primary px-md py-xl lg:w-[45%] lg:px-margin lg:py-3xl">
        <div className="flex h-full max-w-[520px] flex-col justify-between gap-xl">
          <div>
            <p className="type-label-caps text-primary-muted">{eyebrow}</p>
            <h1 className="type-headline-md mt-md text-paper-raised lg:type-headline-lg">
              {headline}
            </h1>
            <p className="type-body-lg measure mt-lg text-primary-pale">
              How language lives in the brain — taught for curious, self-directed
              learners, not clinicians or linguists-in-training.
            </p>
          </div>

          <figure className="hidden lg:block">
            <blockquote className="type-quote measure text-primary-pale">
              “It demystifies something you have been doing effortlessly your whole
              life, and makes it astonishing again.”
            </blockquote>
            <figcaption className="type-caption mt-sm text-primary-muted">
              A note from the instructor
            </figcaption>
          </figure>
        </div>
      </section>

      <section className="flex flex-1 flex-col justify-center px-md py-xl lg:px-margin lg:py-3xl">
        <div className="w-full max-w-[440px]">
          {children}

          <p className="type-caption mt-lg text-meta-text">
            By continuing you agree to our{" "}
            <Link href="/terms" className="text-tertiary-strong underline">
              Terms of Service
            </Link>{" "}
            and{" "}
            <Link href="/privacy" className="text-tertiary-strong underline">
              Privacy Policy
            </Link>
            .
          </p>
        </div>
      </section>
    </main>
  );
}
