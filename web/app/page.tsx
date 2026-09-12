import Link from "next/link";

import { Masthead } from "@/components/masthead";
import { fetchCurrentUser, type CurrentUser } from "@/lib/api";

/*
 * The landing page is a stub — its real design (course catalog, progress
 * overview, featured courses) belongs to its own piece of work. What it does
 * carry is the whole point of this one: when you are signed in, everything
 * below the greeting came out of Postgres, through Django, authenticated by a
 * Clerk session token. If this renders your name, the integration works.
 */
export default async function Home() {
  let user: CurrentUser | null = null;
  let apiReachable = true;

  try {
    user = await fetchCurrentUser();
  } catch {
    // A signed-in session whose API call failed should still render a page
    // that says so, rather than a 500.
    apiReachable = false;
  }

  return (
    <>
      <Masthead />
      <main className="mx-auto w-full max-w-[1200px] flex-1 px-md py-2xl sm:px-margin">
        {user ? (
          <AccountSummary user={user} />
        ) : (
          <SignedOutHero apiReachable={apiReachable} />
        )}
      </main>
    </>
  );
}

function SignedOutHero({ apiReachable }: { apiReachable: boolean }) {
  return (
    <div>
      <p className="type-label-caps text-accent">Neurolinguistics</p>
      <h1 className="type-headline-lg measure mt-md">
        The cognitive science of how language lives in the brain.
      </h1>
      <p className="type-body-lg measure mt-lg text-accent-strong">
        A self-paced course for curious learners. Create an account to enroll and
        track your progress across devices.
      </p>
      <div className="mt-xl flex flex-wrap gap-md">
        <Link
          href="/sign-up"
          className="type-label-lg rounded-md bg-tertiary px-md py-sm text-accent-strong hover:bg-tertiary-strong hover:text-paper-raised"
        >
          Create your account
        </Link>
        <Link
          href="/sign-in"
          className="type-label-lg rounded-md border border-primary bg-paper px-md py-sm text-primary hover:bg-primary-pale hover:text-primary-strong"
        >
          Sign in
        </Link>
      </div>

      {!apiReachable && (
        <p className="type-body-sm mt-xl rounded-sm bg-warning-subtle px-sm py-sm text-warning">
          The course API is not responding, so account details are unavailable.
          Signing up still works.
        </p>
      )}
    </div>
  );
}

function AccountSummary({ user }: { user: CurrentUser }) {
  const rows: Array<[string, string]> = [
    ["Email", user.email],
    ["Role", user.role],
    ["Member since", new Date(user.created_at).toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    })],
    ["Account id", user.id],
  ];

  return (
    <div>
      <p className="type-label-caps text-accent">Your account</p>
      <h1 className="type-headline-md measure mt-md">
        {user.name ? `Welcome, ${user.name}.` : "Welcome."}
      </h1>
      <p className="type-body-lg measure mt-lg text-accent-strong">
        Your account is set up. Courses will appear here once the catalog is
        live.
      </p>

      <dl className="mt-xl max-w-[560px]">
        {rows.map(([label, value]) => (
          <div
            key={label}
            className="flex justify-between gap-md border-t border-rule py-sm"
          >
            <dt className="type-label-md text-accent">{label}</dt>
            <dd className="type-data-md text-meta-text">{value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
