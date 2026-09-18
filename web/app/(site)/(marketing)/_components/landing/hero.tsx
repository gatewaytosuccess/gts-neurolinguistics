import Link from "next/link";
import { Show } from "@clerk/nextjs";

import type { HeroContent } from "./types";

export function Hero({ content }: { content: HeroContent }) {
  return (
    <section className="mx-auto max-w-[1200px] px-md py-2xl sm:px-margin lg:py-3xl">
      <p className="type-label-caps text-accent">{content.eyebrow}</p>
      <h1 className="type-headline-md measure mt-md lg:type-headline-lg">
        {content.headline}
      </h1>
      <p className="type-body-lg measure mt-lg">{content.body}</p>

      <div className="mt-xl flex flex-wrap gap-md">
        <Show
          when="signed-in"
          fallback={
            <>
              <Link href="/sign-up" className="button-primary">
                Create your account
              </Link>
              <Link href="/sign-in" className="button-secondary">
                Sign in
              </Link>
            </>
          }
        >
          <Link href="/dashboard" className="button-primary">
            Go to your dashboard
          </Link>
        </Show>
      </div>
    </section>
  );
}
