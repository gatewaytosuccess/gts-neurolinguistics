# Clerk owns identity; the `users` table is a read-only mirror

Clerk handles sign-up, sign-in, passwords, email verification, password reset and social login. Django never holds a learner credential: it verifies Clerk's session JWTs against Clerk's JWKS, and the local `users` row exists only to carry what Clerk has no concept of — the platform role, the account status, and the foreign key that enrollments, orders, carts and reviews all hang off.

That row is written from exactly two places, both of which copy *from* Clerk: the `user.*` webhook, which is the durable path, and just-in-time provisioning during authentication, which exists only to cover the seconds between Clerk redirecting a brand-new user into the app and the `user.created` delivery landing. Nothing writes to it in the other direction. There is deliberately no `PATCH /api/users/me`: a profile edit accepted here would be silently overwritten by the next `user.updated`, so profile edits go through Clerk's own UI instead.

## Consequences

- **Deletion cannot be a delete.** A paying customer's row is the parent of their order history, so `user.deleted` releases the Clerk id and marks the row `deleted` rather than removing it. That makes deletion reversible, which is the right behaviour — someone who deletes a login should not lose courses they paid for — and it forced a fourth value into the account status enum.
- **Which statuses are self-clearing became a rule we had to write down.** Because signing up again resurrects a `deleted` account, the same path must refuse to resurrect a `suspended` or `banned` one, or deleting a Clerk account would become a way out of a ban. `users.sync` is the single place both the webhook and the authentication fallback go through, precisely so those two cannot drift apart.
- **Email-based bans are evadable.** Someone banned can sign up again with a different address and get a clean account. Accepted for now; anything better needs payment-instrument or device signals.
- **Lock-in is real.** Moving off Clerk later means owning credentials, verification and social login ourselves, and backfilling `clerk_user_id` for every existing account. The trade was made knowingly: a two-person team should not be writing password-reset flows.
