# GTS Neurolinguistics

A platform that sells and delivers an online neurolinguistics course. It has two faces: learners buy courses and work through them, and admins publish and manage the content.

## Language

### Identity

**Clerk user**:
The identity Clerk holds for a person — their credentials, email addresses, verification state and social connections. Nothing in this codebase creates or edits one.
_Avoid_: Clerk account, auth user

**User**:
The platform's own record of a person, mirrored from a Clerk user and carrying what Clerk knows nothing about: their role, their account status, and everything hung off them by foreign key.
_Avoid_: Account, profile, member

**Mirror**:
The relationship between the two: Clerk is the source of truth, the local `User` is a copy of it, and copies are never edited in place.
_Avoid_: Sync, replica, shadow

**Role**:
What a user is allowed to do on the platform — `learner`, `instructor`, or `admin`. Assigned by the platform, never by the person signing up.
_Avoid_: Permission, access level, tier

**Learner**:
The default role, and the word for a person taking a course. Every new sign-up is one.
_Avoid_: Student, customer, subscriber

### Account status

**Active**:
The only status that can sign in and use the API.

**Suspended** / **Banned**:
Imposed by an admin, and cleared only by an admin. Nothing the person does to their own Clerk identity lifts one — not deleting it, not signing up again.
_Avoid_: Blocked, disabled, deactivated

**Deleted**:
The person deleted their own Clerk identity. The platform record survives, because it is what their enrollments and orders point at. Reversible: signing up again with the same email brings the account back as it was.
_Avoid_: Removed, closed, purged

**Resurrect**:
What happens when a deleted account's owner signs up again — the original record is reclaimed, enrollments and purchase history intact, rather than a second record being created.
_Avoid_: Restore, undelete, reactivate

### Courses and access

**Course**:
A purchasable unit of teaching, made of modules, which are made of lessons.

**Enrollment**:
A user's access to a course, however they got it — bought, granted by an admin, or comped.
_Avoid_: Purchase, subscription, membership

**Order**:
A user's transaction for one or more courses. Distinct from the enrollments it produces: refunding an order and revoking access are separate acts.
_Avoid_: Payment, receipt, invoice
