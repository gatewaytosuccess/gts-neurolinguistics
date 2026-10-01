import { fetchCurrentUser, type AdminUserDetail } from "@/lib/api";

import { reinstateUser, suspendUser } from "../_lib/suspension-actions";
import { ReinstateDialog, SuspendDialog } from "./suspension-dialogs";

const SELF_REASON = "You can't change your own role or status.";

/** Suspend for an active or deleted user, Reinstate for a suspended one. */
export async function SuspensionControl({ user }: { user: AdminUserDetail }) {
  // Already fetched by `requireAdmin` for this request.
  const isSelf = (await fetchCurrentUser())?.id === user.id;
  const name = user.name || user.email;

  if (user.status === "suspended") {
    return (
      <ReinstateDialog
        name={name}
        returnsToDeleted={!user.has_clerk_identity}
        reinstate={reinstateUser.bind(null, user.id)}
        disabledReason={isSelf ? SELF_REASON : undefined}
      />
    );
  }

  return (
    <SuspendDialog
      name={name}
      suspend={suspendUser.bind(null, user.id)}
      disabledReason={
        isSelf
          ? SELF_REASON
          : user.role === "admin"
            ? "Demote to learner first."
            : undefined
      }
    />
  );
}
