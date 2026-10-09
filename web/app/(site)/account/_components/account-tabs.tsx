import Link from "next/link";

const TABS = [
  { key: "settings", href: "/account", label: "Settings" },
  { key: "orders", href: "/account/orders", label: "Order history" },
] as const;

export function AccountTabs({
  current,
}: {
  current: (typeof TABS)[number]["key"];
}) {
  return (
    <nav aria-label="Your account" className="mt-lg">
      <ul className="flex gap-xs">
        {TABS.map((tab) => {
          const active = tab.key === current;
          return (
            <li key={tab.key}>
              <Link
                href={tab.href}
                aria-current={active ? "page" : undefined}
                className={`type-label-md block whitespace-nowrap rounded-sm px-sm py-sm ${
                  active
                    ? "bg-tertiary-pale text-tertiary-strong"
                    : "text-accent hover:bg-paper-dim hover:text-accent-strong"
                }`}
              >
                {tab.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
