export type AdminSection = {
  label: string;
  href: string;
  description: string;
  available: boolean;
};

// Drives both the side nav and the dashboard cards.
export const ADMIN_SECTIONS: AdminSection[] = [
  {
    label: "Courses",
    href: "/admin/courses",
    description:
      "Create courses, edit their curriculum and lessons, and publish them.",
    available: true,
  },
  {
    label: "Users",
    href: "/admin/users",
    description:
      "Find accounts, change roles, suspend or ban, and grant enrollments.",
    available: false,
  },
  {
    label: "Orders",
    href: "/admin/orders",
    description: "Review purchases and issue refunds.",
    available: false,
  },
  {
    label: "Coupons",
    href: "/admin/coupons",
    description: "Create and manage discount codes.",
    available: false,
  },
  {
    label: "Reviews",
    href: "/admin/reviews",
    description: "Hide or publish course reviews.",
    available: false,
  },
];
