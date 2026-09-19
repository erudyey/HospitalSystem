# Git Reference and Workflow Guide

This document defines version control procedures, core Git operations, commit
standards, contribution and pull request workflows, and quality requirements for
the HospitalSystem repository.

---

## 1. Git Architecture

Git tracks files across four discrete working areas:

```
[ Working Tree ]  --(git add)-->  [ Staging Area ]  --(git commit)-->  [ Local Repo ]  --(git push)-->  [ Remote Repo ]
  (Edited files)                   (Index)                               (.git history)                   (origin/master)
```

1. **Working Tree**: Files currently checked out and edited on disk.
2. **Staging Area (Index)**: Files marked for inclusion in the next commit.
3. **Local Repository**: Permanent commit snapshots stored locally in `.git`.
4. **Remote Repository**: Shared repository on GitHub (`origin`).

---

## 2. Standard Development Flow

### Fetch Latest Remote Changes

Synchronize local `master` with remote before starting edits:

```bash
git pull origin master
```

### Inspect Modifications

Review modified and untracked files:

```bash
git status
```

Inspect exact line diffs in the working tree:

```bash
git diff
```

### Run Quality Gates

Verify tests and formatting before staging changes:

```powershell
.\run.ps1 test
.\run.ps1 format
```

Or directly via Python toolchain:

```bash
uv run pytest backend/tests/ -v
uv run ruff check backend desktop package.py
.venv/Scripts/python.exe -m basedpyright
```

### Stage Changes

Add specific files to the staging index:

```bash
git add backend/clinic/services.py
git add backend/clinic/views.py backend/clinic/urls.py
```

Remove a file from the staging index without discarding disk edits:

```bash
git restore --staged <file-path>
```

### Commit Changes

Record an atomic commit following Conventional Commits format:

```bash
git commit -m "<type>(<scope>): <summary in present tense>"
```

#### Commit Types

| Type       | Purpose                                          | Example                                                                          |
| :--------- | :----------------------------------------------- | :------------------------------------------------------------------------------- |
| `feat`     | New user-facing or API feature                   | `git commit -m "feat(receptionist): add conflict warning banner to booking form"`|
| `fix`      | Bug fix or correction                            | `git commit -m "fix(services): prevent deletion of completed appointments"`       |
| `test`     | Add, update, or refactor tests                   | `git commit -m "test(clinical): add test cases for 15-minute slot overlap"`     |
| `docs`     | Documentation changes only                       | `git commit -m "docs(api): document doctor queue request schemas"`              |
| `refactor` | Code change without behavioral alteration        | `git commit -m "refactor(views): extract reusable token parser"`                 |
| `chore`    | Tooling, dependencies, or formatting adjustments | `git commit -m "chore(format): run ruff format across backend"`                 |

Rules:
- Keep commits atomic: one logical change per commit.
- Never mix formatting changes with feature implementations.

### Push to Remote

Publish local commits to GitHub:

```bash
git push origin <branch-name>
```

> [!NOTE]
> Direct pushes to `master` are restricted. All feature work and bug fixes
> must be submitted via topic branches and Pull Requests (see Section 4).

---

## 3. Branch Operations

For isolated feature development:

```bash
# Create and check out a feature branch:
git checkout -b feature/<feature-name>

# Verify active branch:
git branch

# Push new branch to remote and set upstream:
git push -u origin feature/<feature-name>

# Switch back to master:
git checkout master
```

---

## 4. Contributing and Pull Request Workflow

HospitalSystem uses a feature branch and Pull Request (PR) model to maintain
code quality, bisectability, and architectural consistency.

### 4.1 Branch Naming Standards

Always branch from an up-to-date `master`. Use a descriptive prefix that matches
the purpose of the work:

| Prefix       | Purpose                                      | Example                              |
| :----------- | :------------------------------------------- | :----------------------------------- |
| `feature/`   | New user-facing or architectural capability  | `feature/doctor-queue-ui`            |
| `fix/`       | Bug fix or state machine correction          | `fix/conflict-overlap-detection`     |
| `test/`      | New or improved automated test suites        | `test/appointment-state-machine`     |
| `docs/`      | Documentation, runbooks, or specs            | `docs/pr-contribution-guidelines`    |
| `refactor/`  | Code restructuring without behavioral change | `refactor/auth-token-validation`     |
| `chore/`     | Tooling, dependencies, or formatting updates | `chore/update-deno-deps`             |

### 4.2 End-to-End Contribution Lifecycle

```
[ master ] --(git checkout -b)--> [ feature branch ] --(code & commit)--> [ run quality gates ]
                                                                                   |
[ GitHub PR ] <--(git push -u origin)----------------------------------------------+
      |
[ Review & CI ] --(merge to master)--> [ git checkout master && git pull origin master ]
                                                    |
                                      (git branch -d feature/...)
```

#### Step 1: Synchronize Local Master

Ensure your local `master` is clean and up to date before branching:

```bash
git checkout master
git pull origin master
```

#### Step 2: Create a Dedicated Topic Branch

Create and switch to your new branch:

```bash
git checkout -b feature/<feature-name>
```

#### Step 3: Implement Changes and Commit Atomically

Commit logically isolated units following the Conventional Commits specification:

```bash
git commit -m "<type>(<scope>): <imperative subject>"
```

Follow these strict rules:
- **One Logical Change Per Commit**: Separate refactoring, bug fixes, and
  features into individual commits.
- **No Mixed Formatting**: Never combine automated code reformatting with
  business logic changes.
- **Bisectable Commits**: Every commit must build and pass tests cleanly.
- **Zero Em/En Dash Policy**: No em dashes (`\u2014`) or en dashes (`\u2013`)
  in code, comments, docstrings, markdown files, or commit messages. Use `--`,
  colons, or parentheses instead.

#### Step 4: Run Mandatory Quality Gates Locally

Before pushing or opening a PR, all quality gates must pass locally:

Using the task runner:

```powershell
# Windows (PowerShell 7+):
.\run.ps1 test
.\run.ps1 format
```

```bash
# macOS / Linux (Bash):
./run.sh test
./run.sh format
```

Or execute directly through the underlying toolchain:

```bash
# 1. Backend automated tests (100% pass rate required):
uv run pytest backend/tests/ -v

# 2. Strict Python type checking:
.venv/Scripts/python.exe -m basedpyright    # Windows
.venv/bin/python -m basedpyright           # macOS / Linux

# 3. Python linting and formatting:
uv run ruff check backend desktop package.py
uv run ruff format --check backend desktop package.py

# 4. Frontend compilation and formatting:
cd frontend && deno task build && cd ..
deno fmt --check .github/workflows/ frontend/src/
```

#### Step 5: Push Branch to Remote

Push your topic branch to GitHub and set up remote tracking:

```bash
git push -u origin feature/<feature-name>
```

#### Step 6: Create the Pull Request

Open a Pull Request targeting the `master` branch:

- **Via GitHub Web UI**: Go to the repository page on GitHub and click
  **Compare & pull request** on your recently pushed branch.
- **Via GitHub CLI (`gh`)**:
  ```bash
  gh pr create --base master --head feature/<feature-name>
  ```

Set the PR title to follow Conventional Commits (e.g.,
`feat(receptionist): add conflict warning banner to booking form`).

#### Step 7: Complete the Pull Request Description

Fill in the PR description following this standard template:

```markdown
## Summary of Changes
- High-level overview of what this PR accomplishes.
- List of key files and modules impacted.

## Motivation & Context
- Why is this change required? What issue or task does it address?
- Reference issue: Fixes #<issue-id> or Addresses Slice <N>.

## Technical Approach & Tradeoffs
- Why this approach was chosen over alternatives.
- Any non-obvious design decisions, constraints, or invariants accepted.

## Verification & Testing Performed
- [x] Backend tests passing (`uv run pytest backend/tests/ -v`)
- [x] Strict type check passing (`basedpyright`)
- [x] Ruff lint and format clean (`ruff check`, `ruff format`)
- [x] Frontend build and format clean (`deno task build`, `deno fmt`)
- [x] Manual verification steps executed:
  1. Ran application (`.\run.ps1 dev` or `.\run.ps1 desktop`).
  2. Tested user workflows and verified edge cases.

## Breaking Changes / Migration Notes
- **Database Migrations**: e.g., migration `0003_...` added, or None.
- **API Changes**: None (or detail modified endpoints / schemas).
- **Environment Variables**: None (or specify new variables).
```

#### Step 8: Address Review Feedback and Iterate

When reviewers request adjustments or CI reports an issue:

1. Make edits on the same local branch.
2. Re-run quality gates (`.\run.ps1 test` and `.\run.ps1 format`).
3. Record new atomic commits with appropriate types (`fix(...)`, `refactor(...)`).
4. Push updates to GitHub:
   ```bash
   git push origin feature/<feature-name>
   ```
   The existing Pull Request updates automatically.

If `master` has advanced since your branch was created, sync with upstream:

```bash
git fetch origin
git merge origin/master
# Or rebase if preferred by repository maintainers:
# git rebase origin/master
```

Resolve any merge conflicts, re-verify tests, and push.

#### Step 9: Post-Merge Cleanup

Once your Pull Request has been approved and merged into `master`:

```bash
# Return to master and pull latest merged changes:
git checkout master
git pull origin master

# Delete the local feature branch:
git branch -d feature/<feature-name>

# Prune stale remote tracking references:
git remote prune origin
```

#### Step 10: Downstream Rebase Workflow (master -> experimental)

The repository maintains a strict separation of concerns between `master` and
active feature branches:

- `master`: Hardened, stable bedrock containing verified slices (Slices 1 to 3
  backend + core UI). No unreleased experimental slices belong on `master`.
- `experimental`: Active multi-role feature branch (Slices 4 to 7).

All bug fixes, performance optimizations, and layout improvements are applied to
`master` first. Once proven, they are rebased downstream onto `experimental`:

```bash
# 1. Ensure master is clean and up to date:
git checkout master
git pull origin master

# 2. Switch to experimental and rebase on master:
git checkout experimental
git rebase master

# 3. Resolve any conflicts in experimental UI components, run tests, and push:
.\run.ps1 test
git push --force-with-lease origin experimental

# 4. CRITICAL: Immediately return to master if master is your active working branch:
git checkout master
```

Rules:
- Force-pushes (`--force`, `--force-with-lease`) are strictly forbidden on `master`.
- `--force-with-lease` is permitted on `experimental` only after a verified downstream rebase.
- Never merge `experimental` into `master` until all milestones are complete and formally approved.

#### Step 11: Reviewing Pull Requests via GitHub CLI (gh)

When reviewing or evaluating Pull Requests using the `gh` command-line interface:

1. **Check PR Status and Checks**:
   ```bash
   gh pr status
   gh pr view <pr-number>
   gh pr checks <pr-number>
   ```
2. **Inspect Exact Diff**:
   ```bash
   gh pr diff <pr-number>
   ```
3. **Approval Criteria**:
   Before approving a PR, verify:
   - All GitHub Actions CI checks (`gh pr checks`) are passing.
   - Strictly zero em dashes (`\u2014`) and en dashes (`\u2013`) exist in diff or commit messages.
   - Strict `basedpyright` type checks pass with 0 errors.
   - All unit and integration tests pass with 100% pass rate.
   - Service layer isolation is respected (database writes in `services.py` inside `transaction.atomic()`).
   - Clinical invariants (completed visit immutability, deletion protections) are preserved.
4. **Submit Approval**:
   ```bash
   gh pr review <pr-number> --approve --body "Reviewed and verified across all repository quality gates and architectural invariants."
   ```

---

## 5. Reverting and Stashing

### Discard Working Tree Modifications

Discard unstaged edits to a file:

```bash
git restore <file-path>
```

### Stash Uncommitted Changes

Temporarily shelve uncommitted work to pull or switch branches:

```bash
# Save uncommitted edits:
git stash

# Restore stashed edits:
git stash pop
```

### Inspect Commit History

View recent concise commit log:

```bash
git log --oneline -n 10
```

---

## 6. Repository Policy

1. **Zero Em/En Dash Policy**: No em dashes (`\u2014`) or en dashes (`\u2013`)
   in code, docstrings, markdown, or commit messages. Use `--`, `:`, or
   parentheses.
2. **Protected Storage**: Never commit `*.sqlite3` or `.env` files. Production
   database located in OS AppData / Library is protected user data.
3. **Deno Frontend Build**: Manage frontend dependencies through Deno
   (`deno.json`). Do not introduce Node.js or `npm`.
4. **Mandatory Verification**: All commits pushed to remote must pass
   `uv run pytest backend/tests/ -v` and `basedpyright`.
5. **Branch Protection & Pull Requests**: All changes to `master` must arrive
   via Pull Requests with passing quality gates and peer review. Direct pushes
   to `master` are strictly prohibited for normal feature development.

---

## 7. Command Reference

| Action                        | Command                                             |
| :---------------------------- | :-------------------------------------------------- |
| Pull latest remote commits    | `git pull origin master`                            |
| View status of modified files | `git status`                                        |
| View unstaged line diffs      | `git diff`                                          |
| Stage file for commit         | `git add <file>`                                    |
| Unstage file                  | `git restore --staged <file>`                       |
| Discard unstaged changes      | `git restore <file>`                                |
| Commit staged changes         | `git commit -m "<type>(<scope>): <summary>"`        |
| Push commits to remote branch | `git push origin <branch>`                          |
| Push branch and set upstream  | `git push -u origin <branch>`                       |
| Create and switch branch      | `git checkout -b <branch>`                          |
| Switch branch                 | `git checkout <branch>`                             |
| Delete local branch (merged)  | `git branch -d <branch>`                            |
| Force delete local branch     | `git branch -D <branch>`                            |
| Open PR via GitHub CLI        | `gh pr create --base master --head <branch>`        |
| Check status of open PRs      | `gh pr status`                                      |
| View PR in browser            | `gh pr view --web`                                  |
| Prune deleted remote branches | `git remote prune origin`                           |
| View compact commit history   | `git log --oneline -n 10`                           |
| Stash uncommitted changes     | `git stash`                                         |
| Apply stashed changes         | `git stash pop`                                     |
