# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a fullstack web application. It's purpose is to serve as a learning platform for neurolinguistics through online courses, as well as to market and sell these courses. There's two main views - a user view (users can signup, buy courses, view courses, progress through owned courses, etc...) and an admin view (admins can upload/edit/delete courses).

## Tech Stack

**Frontend**: Typescript + Next.js\
**Backend**: Python + Django\
**Database**: PostgreSQL on Amazon RDS\
**Object storage**: Amazon S3\
**Auth**: Clerk

## Frontend (`web/`)

Next.js project. See `web/README.md` for more details.

## Backend (`api/`)

Django project with a virtualenv at `api/.venv` (gitignored). Run commands as `.venv/bin/python manage.py <cmd>` from `api/`. Settings are split under `config/settings/` and default to `config.settings.dev`; configuration is read from `api/.env` (see `api/.env.example`). Apps: `common`, `users`, `courses`, `enrollments`, `commerce`, `reviews`. See `api/README.md` for setup details.

## Database Schema

See `SCHEMA.md` at the root of the project.

## Other .md Files

`CONTEXT.md` - Project language and terminology. Used and updated after/during grilling sessions (grill-with-docs skill) when vocabulary is solidified.\
`DESIGN.md` - a design for the frontend visuals.
`README.md` - standard readme, mostly tailored towards dev setup instructions at the moment.
`SPEC.md` - a high level spec of the project. Free to change if a better alternative to anything in the spec exists.\

## Code comments

A comment earns its place by saying something the code cannot.

- **Explain why, not what.** A comment that restates the line below it is noise. Comment the things a reader would otherwise undo: a decision with a non-obvious reason, a constraint that isn't visible locally, a value that looks like a mistake and isn't.
- **Describe what only when the code can't say it.** An opaque regex, a branch whose trigger isn't obvious, a workaround for someone else's bug. Self-evident code gets nothing.
- **Never write about changes.** No "was X, now Y", no "renamed from", no "added to fix the bug where", no notes about what a library version altered. A comment describes the code as it stands. History belongs in git; framework-version gotchas belong in the relevant README.
- **Never describe code that isn't there.** Comments are part of what you change: if behaviour moves, the comments around it move with it, and a stale comment is worse than none.
- **Docstrings answer to the same test.** Give a caller what the signature doesn't already: what comes back on failure, what is deliberately excluded, what the thing must not be used for. Don't narrate the body.
- **State the constraint, not its provenance.** Never name a .md, a ticket, an ADR, a spec, or a conversation as the reason for something. The reader needs the rule, not where it's recorded or who decided it. A bare pointer is fine when there's genuinely more to read (`See ADR-0007`); reproducing the document'sargument is not.
- **Write to the next editor, never to a reviewer.** The audience is someone about to change this line. If a comment reads as defending or justifying the code, cut it.
- **No arguing.** State the constraint flatly. No superlatives, no comparisons, no reasoning chains. One clause where one clause will do.

### Register

Bad:

```
/*
 * The frame both account pages sit in. Nothing is centered: DESIGN.md is
 * explicit that a centered hero is the fastest way for this to read as a
 * generic SaaS template rather than a course catalog.
 */
```

Good:

```
// Not centered: a centered hero reads as generic SaaS.
```

The bad version cites where the rule is recorded, argues the case for it, and narrates what the component is. The good version states the constraint and stops.

## Git Workflow

- Never run `git add`, `git commit`, or `git push`. Leave all changes unstaged.
- When a feature is done, summarize the files changed and stop. I review and commit manually.
- Only create PRs with `gh pr create` after I've explicitly said to do so.

## Agent skills

### Issue tracker

Issues live in GitHub Issues on `gatewaytosuccess/gts-neurolinguistics`, managed via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical triage roles, using their default label strings. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
