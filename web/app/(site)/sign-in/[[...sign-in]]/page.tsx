import type { Metadata } from "next";
import { SignIn } from "@clerk/nextjs";

import { AuthSplitPanel } from "@/components/auth-split-panel";

export const metadata: Metadata = {
  title: "Sign in",
};

/* Forgot-password lives inside this component's own flow, under the same path. */
export default function SignInPage() {
  return (
    <AuthSplitPanel eyebrow="Welcome back" headline="Sign in to continue">
      <SignIn
        path="/sign-in"
        signUpUrl="/sign-up"
        fallbackRedirectUrl="/dashboard"
      />
    </AuthSplitPanel>
  );
}
