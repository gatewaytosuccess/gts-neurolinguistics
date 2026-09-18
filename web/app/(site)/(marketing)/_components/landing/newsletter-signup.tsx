// Inert until a mailing-list provider is wired in.
export function NewsletterSignup() {
  return (
    <section
      aria-labelledby="newsletter-heading"
      className="mx-auto max-w-[1200px] px-md py-2xl sm:px-margin lg:py-3xl"
    >
      <p className="type-label-caps text-accent">Not ready to enroll?</p>
      <h2
        id="newsletter-heading"
        className="type-headline-sm measure mt-sm lg:type-headline-md"
      >
        Get a short note when a new course or lesson goes live.
      </h2>

      <form className="mt-xl max-w-[560px]">
        <label htmlFor="newsletter-email" className="type-label-md block">
          Email address
        </label>
        <div className="mt-xs flex flex-col gap-sm sm:flex-row">
          <input
            id="newsletter-email"
            type="email"
            autoComplete="email"
            placeholder="you@example.com"
            disabled
            aria-describedby="newsletter-status"
            className="type-body-md min-w-0 flex-1 cursor-not-allowed rounded-sm border border-border-strong bg-paper-raised px-sm py-sm placeholder:text-meta-text disabled:bg-paper-dim"
          />
          <button type="submit" disabled className="button-secondary">
            Subscribe
          </button>
        </div>
        <p id="newsletter-status" className="type-caption mt-sm text-meta-text">
          Coming soon.
        </p>
      </form>
    </section>
  );
}
