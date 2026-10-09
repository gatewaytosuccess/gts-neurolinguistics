"use client";

import { UserProfile } from "@clerk/nextjs";
import { usePathname } from "next/navigation";

import { clerkAppearance } from "@/lib/clerk-appearance";

export function AccountProfile() {
  return (
    <UserProfile path="/account" routing="path" appearance={clerkAppearance} />
  );
}

// Clerk switches sections with pushState, so this can't come from the page's params.
export function DeletionNote() {
  const section = usePathname().split("/")[2];
  if (section !== "security") return null;

  return (
    <p className="type-body-md measure mt-lg text-accent-strong">
      Deleting your sign-in doesn&rsquo;t erase your purchases. Sign up again
      with the same email and your courses and order history come back.
    </p>
  );
}
