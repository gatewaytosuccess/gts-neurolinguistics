import type { AdminUserDetail } from "@/lib/api";

import { SELF_HINT_ID } from "../_lib/role-change";
import { reinstateUser, suspendUser } from "../_lib/suspension-actions";
import { ReinstateDialog, SuspendDialog } from "./suspension-dialogs";

/** Suspend for an active or deleted user, Reinstate for a suspended one. */
export function SuspensionControl({
  user,
  isSelf,
}: {
  user: AdminUserDetail;
  isSelf: boolean;
}) {
  const name = user.name || user.email;
  const disabledBy = isSelf ? SELF_HINT_ID : undefined;

  if (user.status === "suspended") {
    return (
      <ReinstateDialog
        name={name}
        returnsToDeleted={!user.has_clerk_identity}
        reinstate={reinstateUser.bind(null, user.id)}
        disabledBy={disabledBy}
      />
    );
  }

  return (
    <SuspendDialog
      name={name}
      suspend={suspendUser.bind(null, user.id)}
      disabledBy={disabledBy}
      disabledReason={
        !isSelf && user.role === "admin"
          ? "Demote to learner first."
          : undefined
      }
    />
  );
}
