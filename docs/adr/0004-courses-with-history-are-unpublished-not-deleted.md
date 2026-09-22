# Courses with history are unpublished, not deleted

An admin can delete a course only if nobody has ever enrolled in it, bought it or reviewed it; otherwise the API answers 409 and the course can only be unpublished. Unpublishing already takes a course out of the catalog without touching anyone's access, so a second way to retire a course would only add a way to destroy data.

## Consequences

- **The database enforces it, not just the view.** `Enrollment.course` and `Review.course` are `PROTECT`, like `OrderItem.course` already was. Before this, deleting a course that had only been comped or granted silently cascaded away those learners' enrollments.
- **Revoked enrollments still count.** A course whose every enrollment was revoked still has history, and still can't be deleted.
- **Old courses accumulate as drafts.** There is no archived state; the admin course list's status filter is how they stay out of the way.

## Considered options

- **An `archived` status**: a third course state, hidden from the catalog and from the admin list's default view. Rejected for now: it behaves exactly like an unpublished draft for every learner.
- **Hard delete with `SET_NULL`**: keeps order rows but leaves enrollments, reviews and order items pointing at nothing, which breaks purchase history and the learner's dashboard.
