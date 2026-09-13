# Issue tracker: GitHub

Issues and specs for this repo live as GitHub issues. Use the `gh` CLI for all operations.

## Conventions

- **Create an issue**: `gh issue create --title "..." --body "..."`. Use a heredoc for multi-line bodies.
- **Read an issue**: `gh issue view <number> --comments`, filtering comments by `jq` and also fetching labels.
- **List issues**: `gh issue list --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'` with appropriate `--label` and `--state` filters.
- **Comment on an issue**: `gh issue comment <number> --body "..."`
- **Apply / remove labels**: `gh issue edit <number> --add-label "..."` / `--remove-label "..."`
- **Close**: `gh issue close <number> --comment "..."`

Infer the repo from `git remote -v`; `gh` does this automatically when run inside a clone.

## Linking issues

Both operations take the other issue's numeric **database id** (`gh api repos/<owner>/<repo>/issues/<n> --jq .id`), _not_ the `#number` or `node_id`.

- **Sub-issue**: `gh api --method POST repos/<owner>/<repo>/issues/<parent>/sub_issues -F sub_issue_id=<child-db-id>`. Where sub-issues aren't enabled, add the child to a task list in the parent body and put `Part of #<parent>` at the top of the child body.
- **Blocking**: GitHub's native issue dependencies, the canonical, UI-visible representation. `gh api --method POST repos/<owner>/<repo>/issues/<child>/dependencies/blocked_by -F issue_id=<blocker-db-id>`. GitHub reports `issue_dependencies_summary.blocked_by` (open blockers only, the live gate). Where dependencies aren't available, put a `Blocked by: #<n>, #<n>` line at the top of the child body. A ticket is unblocked when every blocker is closed.

## Parent issues and sub-issues

One implementation issue produces one PR. Work that won't fit in one PR is published as a **parent** issue with **sub-issues**, never as a single large implementation issue.

- **Parent**: holds what every slice shares: problem, decisions, domain language, out of scope, and the end-to-end verification. Nobody implements it directly; it closes when its last sub-issue closes.
- **Sub-issue**: one PR's worth of work. It links to the parent for shared decisions instead of repeating them, and states only its own acceptance criteria and verification.

### Slicing rules

- **Vertical, not horizontal.** Each slice delivers behaviour that can be demoed or checked on its own. "All the types", "all the components" or "the backend half" are not slices.
- **Main stays working after every merge.** Changes that break the app when merged alone share a slice, e.g. deleting a route and adding its replacement, or a migration and the code that needs it.
- **Size: about 400 changed lines or fewer**, excluding lockfiles, generated code and pure file moves. If a slice looks bigger, split it again.
- **Prefactor first.** Shared groundwork (a utility, a layout, a schema change) goes in its own slice that the others are blocked by.
- **Blocking edges only where there's a real dependency.** Slices that touch different parts of the same files can still run in parallel.
- **Wide mechanical refactors** (a rename or retype touching many call sites) use expand–contract instead: one expand slice, migrate batches blocked by it, and one contract slice blocked by every batch.

### Publishing

1. Create the parent issue.
2. Create sub-issues in dependency order (blockers first), so each one's blockers already have real issue numbers.
3. Link each one to the parent and add its blocking edges (see **Linking issues**).
4. Label each sub-issue `ready-for-agent` or `ready-for-human`. Leave the parent unlabelled.

Before publishing, show the user the breakdown: title, blocked by, and what each slice delivers. Publish only once they approve it.

## When a skill says "publish to the issue tracker"

- **A spec or plan from grilling** (`/grill-with-docs`, `/to-spec`): publish it as a parent issue, then break it into sub-issues per **Parent issues and sub-issues**. `/to-tickets` does this; if it isn't run, apply the same rules by hand.
- **Work that fits in one PR** (a bug fix, a small change): a single issue is fine.
- **Unsure**: slice it. Merging two small sub-issues later is cheap; splitting a PR is not.

## When a skill says "fetch the relevant ticket"

Run `gh issue view <number> --comments`. If the issue has sub-issues, it's a parent: implement one unblocked sub-issue, not the parent.

## Pull requests as a triage surface

**PRs as a request surface: no.** _(Set to `yes` if this repo treats external PRs as feature requests; `/triage` reads this flag.)_

When set to `yes`, PRs run through the same labels and states as issues, using the `gh pr` equivalents:

- **Read a PR**: `gh pr view <number> --comments` and `gh pr diff <number>` for the diff.
- **List external PRs for triage**: `gh pr list --state open --json number,title,body,labels,author,authorAssociation,comments` then keep only `authorAssociation` of `CONTRIBUTOR`, `FIRST_TIME_CONTRIBUTOR`, or `NONE` (drop `OWNER`/`MEMBER`/`COLLABORATOR`).
- **Comment / label / close**: `gh pr comment`, `gh pr edit --add-label`/`--remove-label`, `gh pr close`.

GitHub shares one number space across issues and PRs, so a bare `#42` may be either: resolve with `gh pr view 42` and fall back to `gh issue view 42`.

## Wayfinding operations

Used by `/wayfinder`. The **map** is a single issue with **child** issues as tickets. Children and blocking use **Linking issues**.

- **Map**: a single issue labelled `wayfinder:map`, holding the Notes / Decisions-so-far / Fog body. `gh issue create --label wayfinder:map`.
- **Child ticket**: a sub-issue of the map. Labels: `wayfinder:<type>` (`research`/`prototype`/`grilling`/`task`). Once claimed, the ticket is assigned to the driving dev. `task` children follow the **Slicing rules**.
- **Frontier query**: list the map's open children (`gh issue list --state open`, scoped to the map's sub-issues / task list), drop any with an open blocker (`issue_dependencies_summary.blocked_by > 0`, or an open issue in the `Blocked by` line) or an assignee; first in map order wins.
- **Claim**: `gh issue edit <n> --add-assignee @me`, the session's first write.
- **Resolve**: `gh issue comment <n> --body "<answer>"`, then `gh issue close <n>`, then append a context pointer (gist + link) to the map's Decisions-so-far.
