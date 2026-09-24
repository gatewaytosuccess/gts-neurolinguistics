# Database Schema for MVP

## Entities

- Users

- Courses

- Modules (a course can have many modules)

- Lessons (a module can have many lessons)

- Enrollments (links users to courses)

- LessonProgress

- Orders (user transaction for a course or courses)

- OrderItems (individual courses contained in an order)

- Carts

- CartItems

- Coupons

- Reviews

## Tables

### USERS

| Column | Type | Key / Constraints | Notes |
| ----------------- | --------- | --------------------------- | ------------------------------------------------------------------------------------------------- |
| id | uuid | PK | |
| clerk_user_id | string | UK, not null | |
| email | string | UK, not null | |
| name | string | not null | |
| avatar_url | string | nullable | |
| role | enum | not null, default `learner` | `learner \| instructor \| admin` |
| status | enum | not null, default `active` | `active \| suspended \| banned \| deleted` — anything other than `active` blocks login. See below |
| suspended_at | timestamp | nullable | Set when a user is suspended or banned |
| suspension_reason | string | nullable | Admin audit note |
| created_at | timestamp | not null | |
| updated_at | timestamp | not null | |

Account status splits along one axis: who can clear it.

- `suspended` / `banned` are imposed by an admin and only an admin lifts them. Deleting the Clerk account does not clear them, and signing up again with the same email is refused rather than granted.
- `deleted` is self-service: the user deleted their Clerk account. The row survives — it is the foreign key target for enrollments, orders and reviews — with `clerk_user_id` released. Signing up again with the same email resurrects it, enrollments intact.

### COURSES

| Column | Type | Key / Constraints | Notes |
| ------------- | --------- | ------------------------- | ------------------------------- |
| id | uuid | PK | |
| instructor_id | uuid | FK → USERS.id, nullable | Null = platform-owned course |
| title | string | not null | |
| slug | string | UK, not null | |
| description | text | | |
| price_cents | int | not null | Catalog price (single currency) |
| thumbnail_key | string | | Thumbnail bucket object key |
| status | enum | not null, default `draft` | `draft \| published` |
| created_at | timestamp | not null | |
| updated_at | timestamp | not null | |

### MODULES

| Column | Type | Key / Constraints | Notes |
| ---------- | --------- | ------------------------- | -------------------------- |
| id | uuid | PK | |
| course_id | uuid | FK → COURSES.id, not null | |
| title | string | not null | |
| position | int | not null | Ordering within the course |
| created_at | timestamp | not null | |
| updated_at | timestamp | not null | |

### LESSONS

| Column | Type | Key / Constraints | Notes |
| ---------------- | --------- | ------------------------- | -------------------------- |
| id | uuid | PK | |
| module_id | uuid | FK → MODULES.id, not null | |
| title | string | not null | |
| video_key | string | | Private bucket object key |
| slides_key | string | | Private bucket object key |
| body | text | | Markdown |
| position | int | not null | Ordering within the module |
| is_preview | bool | not null, default `false` | Free sample lesson |
| duration_seconds | int | nullable | |
| created_at | timestamp | not null | |
| updated_at | timestamp | not null | |

A lesson with no video, slides or body is empty.

### ENROLLMENTS

| Column | Type | Key / Constraints | Notes |
| ----------- | --------- | -------------------------- | ---------------------------- |
| id | uuid | PK | |
| user_id | uuid | FK → USERS.id, not null | |
| course_id | uuid | FK → COURSES.id, not null | |
| source | enum | not null | `purchase \| manual \| comp` |
| order_id | uuid | FK → ORDERS.id, nullable | Set when `source = purchase` |
| enrolled_at | timestamp | not null | |
| status | enum | not null, default `active` | `active \| revoked` |
| revoked_at | timestamp | nullable | |

Unique: `(user_id, course_id)` — a user is enrolled in a course at most once.

### LESSON_PROGRESS

| Column | Type | Key / Constraints | Notes |
| --------------------- | --------- | ------------------------------- | ----------------------------------------- |
| id | uuid | PK | |
| user_id | uuid | FK → USERS.id, not null | |
| lesson_id | uuid | FK → LESSONS.id, not null | |
| status | enum | not null, default `not_started` | `not_started \| in_progress \| completed` |
| last_position_seconds | int | not null, default `0` | Video resume point |
| completed_at | timestamp | nullable | |
| created_at | timestamp | not null | |
| updated_at | timestamp | not null | |

Unique: `(user_id, lesson_id)` — one progress row per learner per lesson.

### ORDERS

| Column | Type | Key / Constraints | Notes |
| -------------- | --------- | ------------------------- | ----------------------------------------- |
| id | uuid | PK | |
| user_id | uuid | FK → USERS.id, not null | |
| coupon_id | uuid | FK → COUPONS.id, nullable | Coupon applied to this order, if any |
| status | enum | not null | `pending \| paid \| refunded \| failed` |
| subtotal_cents | int | not null | |
| discount_cents | int | not null, default `0` | Snapshot of the discount actually applied |
| total_cents | int | not null | |
| payment_ref | string | nullable | Provider transaction id |
| created_at | timestamp | not null | |
| updated_at | timestamp | not null | |

### ORDER_ITEMS

| Column | Type | Key / Constraints | Notes |
| ---------------- | ---- | ------------------------- | -------------------------- |
| id | uuid | PK | |
| order_id | uuid | FK → ORDERS.id, not null | |
| course_id | uuid | FK → COURSES.id, not null | |
| unit_price_cents | int | not null | Price snapshot at purchase |

Unique: `(order_id, course_id)` — a course appears once per order.

### CARTS

| Column | Type | Key / Constraints | Notes |
| ---------- | --------- | --------------------------- | ----------------------------------------- |
| id | uuid | PK | |
| user_id | uuid | FK → USERS.id, not null, UK | One active cart per user |
| created_at | timestamp | not null | |
| updated_at | timestamp | not null | Staleness signal for abandoned-cart email |

### CART_ITEMS

| Column | Type | Key / Constraints | Notes |
| --------- | --------- | ------------------------- | ----- |
| id | uuid | PK | |
| cart_id | uuid | FK → CARTS.id, not null | |
| course_id | uuid | FK → COURSES.id, not null | |
| added_at | timestamp | not null | |

Unique: `(cart_id, course_id)` — a course appears once per cart.

### COUPONS

| Column | Type | Key / Constraints | Notes |
| ------------------ | --------- | -------------------------- | -------------------------------------------------------- |
| id | uuid | PK | |
| code | string | UK, not null | Code entered at checkout |
| description | string | nullable | Admin-facing label |
| discount_type | enum | not null | `percent \| fixed` |
| discount_value | int | not null | `percent`: whole percent 1–100. `fixed`: amount in cents |
| min_subtotal_cents | int | nullable | Minimum order subtotal to qualify (null = none) |
| max_redemptions | int | nullable | Total redemption cap (null = unlimited) |
| times_redeemed | int | not null, default `0` | Running counter |
| starts_at | timestamp | nullable | Valid-from (null = immediately) |
| expires_at | timestamp | nullable | Valid-until (null = no expiry) |
| status | enum | not null, default `active` | `active \| disabled` — admin toggle |
| created_at | timestamp | not null | |
| updated_at | timestamp | not null | |

Coupons are site-wide for the MVP (applied to the order subtotal). Course-scoping would be a later extension via a `COUPON_COURSES` join table.

### REVIEWS

| Column | Type | Key / Constraints | Notes |
| ---------- | --------- | ----------------------------- | ---------------------------------------- |
| id | uuid | PK | |
| user_id | uuid | FK → USERS.id, not null | |
| course_id | uuid | FK → COURSES.id, not null | |
| rating | int | not null, check `1–5` | Star rating |
| body | text | nullable | Optional written review |
| status | enum | not null, default `published` | `published \| hidden` — admin moderation |
| created_at | timestamp | not null | |
| updated_at | timestamp | not null | |

Unique: `(user_id, course_id)` — one review per learner per course. Eligibility (e.g. must be enrolled) is enforced in application logic.

______________________________________________________________________

## Relationships

| Parent | Child | Cardinality | Foreign key | Notes |
| ------- | --------------- | ----------- | ------------------------- | --------------------------------------- |
| USERS | ENROLLMENTS | 1 : 0..\* | enrollments.user_id | |
| COURSES | ENROLLMENTS | 1 : 0..\* | enrollments.course_id | Grants access |
| ORDERS | ENROLLMENTS | 1 : 0..\* | enrollments.order_id | Purchase-sourced enrollments |
| USERS | ORDERS | 1 : 0..\* | orders.user_id | |
| ORDERS | ORDER_ITEMS | 1 : 1..\* | order_items.order_id | An order has at least one item |
| COURSES | ORDER_ITEMS | 1 : 0..\* | order_items.course_id | Sold as a line item |
| USERS | CARTS | 1 : 0..1 | carts.user_id | At most one cart per user |
| CARTS | CART_ITEMS | 1 : 0..\* | cart_items.cart_id | |
| COURSES | CART_ITEMS | 1 : 0..\* | cart_items.course_id | |
| COURSES | MODULES | 1 : 0..\* | modules.course_id | |
| MODULES | LESSONS | 1 : 0..\* | lessons.module_id | |
| USERS | LESSON_PROGRESS | 1 : 0..\* | lesson_progress.user_id | |
| LESSONS | LESSON_PROGRESS | 1 : 0..\* | lesson_progress.lesson_id | |
| USERS | COURSES | 1 : 0..\* | courses.instructor_id | Instructor (nullable) |
| COUPONS | ORDERS | 1 : 0..\* | orders.coupon_id | A coupon applies to zero-or-many orders |
| USERS | REVIEWS | 1 : 0..\* | reviews.user_id | |
| COURSES | REVIEWS | 1 : 0..\* | reviews.course_id | |
