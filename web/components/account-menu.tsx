"use client";

import { UserButton } from "@clerk/nextjs";

export function AccountMenu() {
  return <UserButton userProfileMode="navigation" userProfileUrl="/account" />;
}
