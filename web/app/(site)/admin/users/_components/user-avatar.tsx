import type { AdminUserSummary } from "@/lib/api";

const SIZE_CLASS_NAMES = {
  sm: "size-[32px] type-label-md",
  lg: "size-[64px] type-headline-sm",
};

export function UserAvatar({
  user,
  size = "sm",
}: {
  user: Pick<AdminUserSummary, "name" | "email" | "avatar_url">;
  size?: keyof typeof SIZE_CLASS_NAMES;
}) {
  const className = `${SIZE_CLASS_NAMES[size]} shrink-0 rounded-full bg-paper-dim`;

  if (!user.avatar_url) {
    return (
      <span
        aria-hidden
        className={`${className} flex items-center justify-center text-accent`}
      >
        {(user.name || user.email).charAt(0).toUpperCase()}
      </span>
    );
  }

  return (
    // Clerk's image host isn't allowlisted for next/image.
    // eslint-disable-next-line @next/next/no-img-element
    <img src={user.avatar_url} alt="" className={`${className} object-cover`} />
  );
}
