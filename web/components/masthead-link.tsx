"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

// Active on `href` and every route beneath it.
export function MastheadLink({
  href,
  children,
}: {
  href: string;
  children: ReactNode;
}) {
  const pathname = usePathname();
  const active = pathname === href || pathname.startsWith(`${href}/`);

  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      className={`type-label-md whitespace-nowrap ${
        active ? "text-tertiary" : "text-primary-subtle hover:text-paper-raised"
      }`}
    >
      {children}
    </Link>
  );
}
