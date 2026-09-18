import type { Metadata } from "next";
import { SignUp } from "@clerk/nextjs";

import { AuthSplitPanel } from "@/components/auth-split-panel";

export const metadata: Metadata = {
  title: "Create your account",
};

// Catch-all segment: Clerk routes its own sub-steps (verification, OAuth callback) beneath this path.
export default function SignUpPage() {
  return (
    <AuthSplitPanel eyebrow="Enrollment" headline="Create your account">
      <SignUp
        path="/sign-up"
        signInUrl="/sign-in"
        fallbackRedirectUrl="/dashboard"
      />
    </AuthSplitPanel>
  );
}
