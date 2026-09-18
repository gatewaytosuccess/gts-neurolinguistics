import { Masthead } from "@/components/masthead";

// Surfaces that need to decline the masthead sit outside this group.
export default function SiteLayout({ children }: LayoutProps<"/">) {
  return (
    <>
      <Masthead />
      {children}
    </>
  );
}
