# Neurolinguistics Course Platform — Site & Feature Spec

## 1. Overview

This document outlines the pages and features needed for a platform to sell and deliver an online neurolinguistics course. Everything is grouped by the page it belongs to, so each page's spec is self-contained.

---

## 2. Landing Page (not logged in)

- Hero section with a CTA (sign in/sign up buttons)
- Instructor Credibility
- Plan/tier comparison
- Cancel anytime/low risk framing
- Social proof (testimonials or aggregate state)
- Course/library preview
- Newsletter signup (capture leads who aren't ready to buy yet)

## 3. Dashboard (logged in)

- User profile summary (name, avatar, membership status)
- Progress overview across enrolled courses (progress bars, "continue where you left off")
- Highlights of suggested/featured courses
- Call-to-action to browse courses or resume learning

---

## 4. All Courses Page

- Grid/list of all available courses (owned and not-owned)
- Clear visual distinction between owned vs. not-owned (e.g., "Continue" vs "Buy Now" button)
- Filtering/sorting (by topic, level, price, popularity, newest)
- Search bar
- Course cards showing thumbnail, title, short description, price, rating (see Reviews, below)
- Bundles surfaced here (multiple courses at a discount)

---

## 5. Course Detail / Learning Page (after entering a course)

- Course navigation sidebar (modules/lessons list with completion checkmarks)
- Main content viewer supporting:
  - **Video** (playback speed control, captions/subtitles, resume-from-last-position, offline/download option for mobile learners)
  - **Slides** (PDF or slide-deck viewer, downloadable option)
  - **Text** (rich formatted lessons, readable typography)
- Progress tracker for the current course (persists across devices)
- "Mark as complete" / auto-complete on finish
- Navigation between lessons (next/previous)
- Notes/bookmarking area for the learner
- Downloadable resources section (PDFs, worksheets, transcripts)
- Free preview lessons available to non-purchasers (1–2 sample lessons, increases conversion)
- Quizzes/assessments at the end of modules or the full course — reinforces learning, can gate progress
- Certificate of completion on finishing — downloadable/shareable PDF or LinkedIn-postable badge
- Search within course content (useful given how dense neurolinguistics terminology gets)
- Glossary/reference tab — searchable terminology reference, since the subject is jargon-heavy
- Discussion/Q&A per lesson — comment thread so learners can ask questions (adds perceived value, boosts retention)
- **AI-assisted study tools (maybe)** — auto-generated lesson summaries, flashcards, or a Q&A chatbot trained on course material. Contingent on being able to keep the cost of running this reasonable and having the content/tooling to support it well; treat as a stretch feature rather than a launch requirement.

---

## 6. Course Purchase Page

- Course overview/sales copy (curriculum, outcomes, instructor bio)
- Reviews/ratings for the course (social proof at the point of purchase — distinct from the landing page, this is where it earns its place)
- Pricing display (one-time, subscription, or tiered options)
- Coupon/discount code field
- Checkout flow (payment integration)
- Order confirmation and receipt
- Automatic enrollment on successful purchase

---

## 7. Account: Sign-Up & Login

- Sign-up (email/password, plus optional social login: Google, Apple, etc.)
- Email verification
- Login page with "forgot password" flow
- Basic profile setup (name, avatar, learning goals — optional, for personalization)

---

## 8. My Account / Settings Page

- Update email, password, payment methods, notification preferences
- My Purchases / Billing history: invoices, receipts, subscription management, cancel/refund requests
- Public profile (optional) — if a community/social angle is wanted later, could show certificates earned

---

## 9. Admin Area

Admin sees the same learner-facing views, plus:

- Add/edit/delete courses
- Add/edit/delete/reorder course content (modules, lessons, videos, slides, text)
- Publish/unpublish courses (draft vs. live)
- Content versioning — update a lesson without breaking learners mid-course
- Grant courses to specific users (manual enrollment/comping access), including bulk enrollment
- Manage users (view accounts, revoke access, reset passwords, ban/suspend)
- Manage coupons/discounts and bundles
- Analytics dashboard — enrollment numbers, revenue, completion rates, drop-off points per lesson
- Notification system — push announcements (new course, live Q&A, etc.) to users
- Bulk emailing
- Role management — beyond admin/user, consider "instructor" or "support" roles if the team grows

---

## 10. About / Instructor Page

- Instructor bio and credentials — important for credibility in an academic niche

---

## 11. Blog

- Articles on neurolinguistics topics to drive organic search traffic and establish authority
- SEO-optimized (metadata, structured data for rich search results)

---

## 12. FAQ Page

---

## 13. Contact / Support Page

- Contact form or chat widget

---

## 14. Legal Pages

- Terms of Service
- Privacy Policy
- Refund Policy

---

## 15. Site-Wide / Cross-Cutting Features

These aren't a single page but affect the whole site:

- Mobile responsiveness / app-like experience
- Accessibility compliance (captions, screen-reader support, keyboard navigation)
- Abandoned cart email (remind users who started checkout but didn't finish)
- Email marketing integration (drip campaigns, announcements, re-engagement)
- Referral program (discount for referring friends)
- Affiliate program (other educators/influencers promote the course for a commission)

---

## 16. Growth / Later-Stage Ideas (not tied to a specific page)

- Live sessions or webinars (e.g., live Q&A with the instructor)
- Cohort-based scheduling (optional start dates with community pacing) as a premium tier, vs. self-paced default
- Gamification — streaks, badges, leaderboards

---

## 17. Suggested Tech/Architecture Notes

- **Auth**: role-based access control (learner vs. admin, possibly instructor) rather than a fully separate admin app
- **Content storage**: separate structured storage for video (streaming service like Mux/Cloudflare Stream), slides (PDF/image storage), and text (rich text/markdown in DB) rather than one blob format
- **Payments**: Square (or similar) for one-time and subscription billing, plus coupon logic
- **Progress tracking**: a per-user, per-lesson completion table drives the progress bars on the landing/course pages
- **Unified lesson component**: build the lesson viewer as a single component that switches renderer based on content type, so the admin content editor and learner viewer stay in sync
