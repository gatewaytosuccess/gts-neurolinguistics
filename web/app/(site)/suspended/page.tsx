import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { SignOutButton } from "@clerk/nextjs";
import { auth } from "@clerk/nextjs/server";

import { fetchCurrentUser, isAccountSuspended } from "@/lib/api";

export const metadata: Metadata = {
  title: "Account suspended",
  robots: { index: false, follow: false },
};

export default async function SuspendedPage() {
  const { userId, redirectToSignIn } = await auth();
  if (!userId) return redirectToSignIn();

  let suspended = false;
  try {
    await fetchCurrentUser();
  } catch (error) {
    suspended = isAccountSuspended(error);
  }

  // Only a confirmed suspension renders here; the dashboard reports an unreachable API.
  if (!suspended) redirect("/dashboard");

  return (
    <main className="mx-auto w-full max-w-[1200px] flex-1 px-md py-2xl sm:px-margin">
      <p className="type-label-caps text-accent">Account status</p>
      <h1 className="type-headline-md measure mt-md">
        Your account is suspended.
      </h1>
      <p className="type-body-lg measure mt-lg text-accent-strong">
        While it is, your dashboard and courses are unavailable. If you think
        this is a mistake, or want to talk it over, get in touch and we&rsquo;ll
        look into it.
      </p>

      <div className="mt-xl flex flex-wrap gap-md">
        <Link href="/contact" className="button-primary">
          Contact us
        </Link>
        <SignOutButton redirectUrl="/">
          <button type="button" className="button-secondary">
            Sign out
          </button>
        </SignOutButton>
      </div>
    </main>
  );
}
