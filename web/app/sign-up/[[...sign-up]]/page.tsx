import type { Metadata } from "next";
import { SignUp } from "@clerk/nextjs";

import { AuthSplitPanel } from "@/components/auth-split-panel";
import { Masthead } from "@/components/masthead";

export const metadata: Metadata = {
  title: "Create your account",
};

/*
 * The catch-all segment is required by Clerk's prebuilt component, which
 * routes its own sub-steps — email verification, the OAuth callback — beneath
 * this path.
 */
export default function SignUpPage() {
  return (
    <>
      <Masthead />
      <AuthSplitPanel eyebrow="Enrollment" headline="Create your account">
        <SignUp
          path="/sign-up"
          signInUrl="/sign-in"
          fallbackRedirectUrl="/"
        />
      </AuthSplitPanel>
    </>
  );
}
