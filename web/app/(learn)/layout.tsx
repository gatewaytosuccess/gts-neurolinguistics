// Outside `(site)`: the navy masthead doesn't survive against the dark base.
export default function LearnLayout({ children }: LayoutProps<"/">) {
  return <div className="page-dark flex flex-1 flex-col">{children}</div>;
}
