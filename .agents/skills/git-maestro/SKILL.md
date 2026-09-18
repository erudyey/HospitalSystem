---
name: git-maestro
description: >-
  Standardizes version control operations, atomic commit creation, Conventional Commits formatting,
  and high-impact pull request descriptions.
  Use when staging diffs, authoring git commits, crafting PR descriptions, or planning branching workflows.
---

# Git Maestro: Professional Git & PR Specification

Git Maestro enforces clean, bisectable git histories, atomic commits, and pull requests that streamline peer review.

## 1. Conventional Commits Standard

All commit messages must strictly follow the Conventional Commits specification:

```text
<type>(<optional scope>): <imperative subject line (50-72 chars)>

[optional body explaining motivation and non-obvious details]

[optional footer(s), e.g., Closes #123, BREAKING CHANGE: ...]
```

### Type Taxonomy

| Type | Purpose | Example |
| :--- | :--- | :--- |
| `feat` | New feature or capability for the user/caller | `feat(auth): add OAuth2 PKCE login flow` |
| `fix` | Bug fix in existing functionality | `fix(db): handle connection pool timeout gracefully` |
| `refactor` | Code restructuring without feature or bug changes | `refactor(parser): extract token tokenizer into sub-module` |
| `perf` | Performance improvement | `perf(search): cache compiled regex patterns` |
| `test` | Adding or correcting tests | `test(order): add edge-case tests for zero-amount billing` |
| `docs` | Documentation changes only | `docs(readme): add docker-compose setup instructions` |
| `chore` | Maintenance, dependencies, build scripts | `chore(deps): bump vite from 5.1 to 5.2` |

### Subject Line Rules
- Use imperative mood: *"add"*, not *"added"* or *"adds"*.
- Do not capitalize the first letter after the colon.
- Do not put a period at the end of the subject line.

## 2. Atomic Commits Discipline

- **One Logical Change Per Commit**: Never combine a database migration, a UI layout tweak, and an unrelated dependency upgrade in a single commit.
- **Bisectable**: Every commit must build cleanly and pass tests. If `git bisect` lands on a commit, it must not fail due to unrelated syntax errors.
- **Separate Refactors from Features**: Commit pure refactoring first, followed by the feature that depends on it.

## 3. High-Impact Pull Request Template

```markdown
## Summary of Changes
- High-level overview of what this PR accomplishes.
- List of key files and modules impacted.

## Motivation & Context
- Why is this change required? What problem or ticket does it solve?
- Reference issue: `Fixes #<issue-id>` or `Addresses #<issue-id>`.

## Technical Approach & Tradeoffs
- Why this approach was chosen over alternatives.
- Any non-obvious design decisions or constraints accepted.

## Verification & Testing Performed
- [x] Unit tests passing (`npm test`)
- [x] Integration / E2E verified
- [x] Manual verification steps executed:
  1. Ran `npm run dev`
  2. Verified login flow redirects correctly

## Breaking Changes / Migration Notes
- **Breaking API Changes**: None (or detail changes).
- **Environment Variables Required**: None (or list new keys).
- **Database Migrations**: e.g., `20260815_add_users_index.sql`.
```
