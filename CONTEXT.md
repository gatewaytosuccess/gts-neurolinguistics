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

**Admin**:
A user whose role is `admin`, and the only role that can enter the admin area. Instructors cannot.
_Avoid_: Staff, superuser, moderator

**Admin area**:
The part of the platform where admins manage courses, users, orders, coupons and reviews.
_Avoid_: Django admin (a developer tool with its own login, not part of the product), back office, CMS

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
A user's access to a course, however they got it — bought, granted by an admin, comped, or through a subscription.
_Avoid_: Purchase, subscription, membership

**Enrolled**:
Holding an active enrollment in a course, whatever its source. A revoked enrollment leaves the user not enrolled; buying the course again reactivates that enrollment rather than creating a second one.
_Avoid_: Owned, purchased

**Catalog**:
The public list of published courses. Drafts never appear in it, not even to admins. Unpublishing a course takes it out of the catalog but does not un-enroll anyone: enrolled learners still reach it, just not through the catalog.
_Avoid_: Library, store

**Subscription**:
Recurring paid access to every published course. It works by enrolling the subscriber in each course, including courses published later; cancelling revokes only the enrollments the subscription created, so courses bought outright are kept. Resubscribing reactivates those enrollments rather than creating new ones.
_Avoid_: Membership, plan, all-access (all-access is marketing copy, not a domain term)

**Bundle**:
A curated set of courses sold together at a discount, as a one-time purchase.
_Avoid_: Package, collection

**Order**:
A user's transaction for one or more courses. Distinct from the enrollments it produces: refunding an order and revoking access are separate acts.
_Avoid_: Payment, receipt, invoice

### Marketing

**Testimonial**:
A hand-picked quote with an attribution, chosen to persuade prospective learners. Not tied to enrollment: the person quoted may never have taken a course.
_Avoid_: Review (a review is a learner's rating of a course they are enrolled in)
