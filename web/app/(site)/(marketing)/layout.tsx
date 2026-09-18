import { SiteFooter } from "@/components/site-footer";

export default function MarketingLayout({ children }: LayoutProps<"/">) {
  return (
    <>
      <main className="flex-1">{children}</main>
      <SiteFooter />
    </>
  );
}
