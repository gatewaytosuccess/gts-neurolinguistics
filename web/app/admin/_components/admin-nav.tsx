"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { ADMIN_SECTIONS } from "../_lib/sections";

// A scrollable row of tabs below lg, a side column from lg up.
export function AdminNav() {
  const pathname = usePathname();

  const isActive = (href: string) =>
    href === "/admin"
      ? pathname === href
      : pathname === href || pathname.startsWith(`${href}/`);

  return (
    <nav
      aria-label="Admin"
      className="border-b border-rule bg-paper-raised lg:w-[220px] lg:shrink-0 lg:border-r lg:border-b-0"
    >
      <ul className="flex gap-xs overflow-x-auto px-md py-sm sm:px-margin lg:flex-col lg:overflow-visible lg:px-md lg:py-lg">
        <li className="shrink-0">
          <NavLink href="/admin" active={isActive("/admin")}>
            Dashboard
          </NavLink>
        </li>
        {ADMIN_SECTIONS.map((section) => (
          <li key={section.href} className="shrink-0">
            {section.available ? (
              <NavLink href={section.href} active={isActive(section.href)}>
                {section.label}
              </NavLink>
            ) : (
              <span className="flex items-baseline gap-sm whitespace-nowrap rounded-sm px-sm py-sm text-meta-text opacity-60">
                <span className="type-label-md">{section.label}</span>
                <span className="type-caption">Coming soon</span>
              </span>
            )}
          </li>
        ))}
      </ul>
    </nav>
  );
}

function NavLink({
  href,
  active,
  children,
}: {
  href: string;
  active: boolean;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      className={`type-label-md block whitespace-nowrap rounded-sm px-sm py-sm ${
        active
          ? "bg-tertiary-pale text-tertiary-strong"
          : "text-accent hover:bg-paper-dim hover:text-accent-strong"
      }`}
    >
      {children}
    </Link>
  );
}
