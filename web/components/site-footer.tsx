import Link from "next/link";

const links = [
  { href: "/about", label: "About" },
  { href: "/faq", label: "FAQ" },
  { href: "/contact", label: "Contact" },
  { href: "/terms", label: "Terms of Service" },
  { href: "/privacy", label: "Privacy Policy" },
  { href: "/refund-policy", label: "Refund policy" },
];

// A rule, not a navy field: navy fields are reserved for the stat band and quote card.
export function SiteFooter() {
  return (
    <footer className="border-t border-rule">
      <div className="mx-auto flex max-w-[1200px] flex-col gap-lg px-md py-xl sm:px-margin lg:flex-row lg:items-end lg:justify-between">
        <div>
          <Link href="/" className="type-headline-sm text-primary">
            GTS Neurolinguistics
          </Link>
          <p className="type-caption mt-sm text-meta-text">
            © {new Date().getFullYear()} GTS Neurolinguistics
          </p>
        </div>

        <nav aria-label="Footer">
          <ul className="flex flex-wrap gap-x-lg gap-y-sm">
            {links.map((link) => (
              <li key={link.href}>
                <Link
                  href={link.href}
                  className="type-label-md text-accent hover:text-tertiary-strong"
                >
                  {link.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      </div>
    </footer>
  );
}
