"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

const REFRESHES = 5;
const INTERVAL_MS = 2000;

/**
 * Re-renders the page a few times while the order is pending, then points the
 * learner at their order history. A refresh that finds the order paid
 * replaces this component.
 */
export function ConfirmingPayment() {
  const router = useRouter();
  const [ticks, setTicks] = useState(0);
  // One interval past the last refresh, so its answer can land first.
  const givenUp = ticks > REFRESHES;

  useEffect(() => {
    if (givenUp) return;
    const timer = setTimeout(() => {
      if (ticks < REFRESHES) router.refresh();
      setTicks(ticks + 1);
    }, INTERVAL_MS);
    return () => clearTimeout(timer);
  }, [ticks, givenUp, router]);

  return (
    <div aria-live="polite">
      {givenUp ? (
        <>
          <h1 className="type-headline-md measure mt-md">
            We&rsquo;re still waiting on Stripe.
          </h1>
          <p className="type-body-lg measure mt-lg text-accent-strong">
            Your payment can take a few minutes to confirm. Once it does, the
            order appears in your order history and the course on your
            dashboard.
          </p>
          <div className="mt-xl flex flex-wrap gap-md">
            <Link href="/account/orders" className="button-primary">
              Order history
            </Link>
            <Link href="/dashboard" className="button-secondary">
              Dashboard
            </Link>
          </div>
        </>
      ) : (
        <>
          <h1 className="type-headline-md measure mt-md">
            Confirming your payment&hellip;
          </h1>
          <p className="type-body-lg measure mt-lg text-accent-strong">
            This usually takes a few seconds. Keep this page open.
          </p>
        </>
      )}
    </div>
  );
}
