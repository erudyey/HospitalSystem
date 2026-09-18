# Git Reference and Workflow Guide

This document defines version control procedures, core Git operations, commit
standards, and quality requirements for the HospitalSystem repository.

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
git push origin master
```

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

## 4. Reverting and Stashing

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

## 5. Repository Policy

1. **Zero Em/En Dash Policy**: No em dashes (`\u2014`) or en dashes (`\u2013`)
   in code, docstrings, markdown, or commit messages. Use `--`, `:`, or
   parentheses.
2. **Protected Storage**: Never commit `*.sqlite3` or `.env` files. Production
   database located in OS AppData / Library is protected user data.
3. **Deno Frontend Build**: Manage frontend dependencies through Deno
   (`deno.json`). Do not introduce Node.js or `npm`.
4. **Mandatory Verification**: All commits pushed to remote must pass
   `uv run pytest backend/tests/ -v` and `basedpyright`.

---

## 6. Command Reference

| Action                        | Command                                      |
| :---------------------------- | :------------------------------------------- |
| Pull latest remote commits    | `git pull origin master`                     |
| View status of modified files | `git status`                                 |
| View unstaged line diffs      | `git diff`                                   |
| Stage file for commit         | `git add <file>`                             |
| Unstage file                  | `git restore --staged <file>`                |
| Discard unstaged changes      | `git restore <file>`                         |
| Commit staged changes         | `git commit -m "<type>(<scope>): <summary>"` |
| Push commits to remote        | `git push origin <branch>`                   |
| Create and switch branch      | `git checkout -b <branch>`                   |
| Switch branch                 | `git checkout <branch>`                      |
| View compact commit history   | `git log --oneline -n 10`                    |
| Stash uncommitted changes     | `git stash`                                  |
| Apply stashed changes         | `git stash pop`                              |
