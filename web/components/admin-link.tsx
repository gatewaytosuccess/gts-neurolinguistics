import { MastheadLink } from "@/components/masthead-link";
import { fetchCurrentUser } from "@/lib/api";

// Fails closed: an unreachable API or a suspended account hides the link.
export async function AdminLink() {
  let role: string | undefined;
  try {
    role = (await fetchCurrentUser())?.role;
  } catch {
    return null;
  }

  if (role !== "admin") return null;
  return <MastheadLink href="/admin">Admin</MastheadLink>;
}
