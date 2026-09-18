# Specialized Git Cheatsheet & Team Workflow Guide

Welcome to the HospitalSystem team! This guide explains how Git works in plain
English, breaks down the day-to-day commands you need, and covers our team's
essential rules so you can contribute confidently without fear of breaking
anything.

---

## 1. How Git Works: The 4 Zones

Git tracks changes across four main areas:

```
[ Working Tree ]  --(git add)-->  [ Staging Area ]  --(git commit)-->  [ Local Repo ]  --(git push)-->  [ Remote Repo (GitHub) ]
  (Your files)                     (Index / Staged)                      (.git history)                   (origin/master)
```

1. **Working Tree**: The actual files you see and edit in VS Code, Antigravity,
   or Cursor.
2. **Staging Area (Index)**: A preparation area where you select which modified
   files are ready to be packaged into your next commit.
3. **Local Repository**: Saved snapshots (commits) recorded permanently on your
   machine's local `.git` history.
4. **Remote Repository (`origin`)**: The shared GitHub repository where your team
   collaborates.

---

## 2. Daily Routine: Step-by-Step

### Step 1: Start Your Day by Pulling Latest Changes

Before making any changes, always fetch and merge what your teammates have
pushed:

```bash
git pull origin master
```

> **Why?** This prevents merge conflicts by making sure your code starts from the
> latest shared code.

---

### Step 2: Check What Changed

Whenever you edit files, check which files Git sees as modified or untracked:

```bash
git status
```

To see the exact line-by-line differences before staging:

```bash
git diff
```

---

### Step 3: Run Verification Before Staging

In HospitalSystem, never commit broken code. Always run the fast test suite:

```powershell
# In PowerShell:
.\run.ps1 test

# Or directly via uv:
uv run pytest backend/tests/ -v
```

And run the code style linter and formatter:

```powershell
.\run.ps1 format
```

---

### Step 4: Stage Your Changes

Select the files you want to include in your next commit:

```bash
# Stage a specific file:
git add backend/clinic/services.py

# Stage multiple specific files:
git add backend/clinic/views.py backend/clinic/urls.py

# Stage everything you modified (use carefully, check git status first!):
git add .
```

To unstage a file if you added it by mistake:

```bash
git restore --staged <file-path>
```

---

### Step 5: Create a Commit (Atomic & Descriptive)

A commit is a permanent snapshot with an explanatory message. We follow the
**Conventional Commits** standard:

```bash
git commit -m "type(scope): short description in present tense"
```

#### Allowed Commit Types:

| Type       | When to Use                                      | Example                                                                          |
| :--------- | :----------------------------------------------- | :------------------------------------------------------------------------------- |
| `feat`     | Adding a new feature or endpoint                 | `git commit -m "feat(receptionist): add conflict warning banner to booking form"`|
| `fix`      | Fixing a bug or unexpected behavior              | `git commit -m "fix(services): prevent deletion of completed appointments"`       |
| `test`     | Adding or updating tests                         | `git commit -m "test(clinical): add test cases for 15-minute slot overlap"`     |
| `docs`     | Documentation updates                            | `git commit -m "docs(api): document doctor queue request schemas"`              |
| `refactor` | Code restructuring without behavior change       | `git commit -m "refactor(views): extract reusable token parser"`                 |
| `chore`    | Build tooling, dependencies, or formatting       | `git commit -m "chore(format): run ruff format across backend"`                 |

> **Rule of Thumb (Atomic Commits)**: One logical change per commit. Do not mix
> fixing a bug, reformatting unrelated files, and adding a new feature in a
> single commit.

---

### Step 6: Push to GitHub

Once your local commit is saved and tests pass, send it to the shared remote:

```bash
git push origin master
```

*(If you are working on a feature branch: `git push origin <branch-name>`)*

---

## 3. Working with Branches (Feature Slices)

When working on a separate feature slice, use a branch to avoid interfering with
other teammates:

```bash
# Create and switch to a new branch:
git checkout -b feature/doctor-workspace

# Verify which branch you are on:
git branch

# Push your branch to GitHub for the first time:
git push -u origin feature/doctor-workspace

# Switch back to master:
git checkout master
```

---

## 4. Helpful Safety Nets (When Things Go Wrong)

### "I made changes to a file and want to throw them away"
To discard uncommitted changes in your working tree:
```bash
git restore path/to/file.py
```

### "I want to temporarily stash my work so I can pull latest changes"
```bash
# Save your uncommitted work to a temporary shelf:
git stash

# Pull the latest changes:
git pull origin master

# Reapply your saved work:
git stash pop
```

### "I want to see the last few commits"
```bash
git log --oneline -n 10
```

### "How do I check what commit remote is currently on?"
```bash
git status -v
```

---

## 5. Non-Negotiable HospitalSystem Repository Rules

### 1. The Zero Em/En Dash Rule
* Strictly **zero** em dashes (`\u2014`) and en dashes (`\u2013`) are permitted
  in any file, comment, docstring, markdown, or commit message.
* Always use standard double hyphens (`--`), colons (`:`), or parentheses.

### 2. Never Commit User Data or Secrets
* Never stage `%LOCALAPPDATA%\HospitalSystem\clinic.sqlite3`, `*.sqlite3`,
  or `.env` files.
* Test databases exist in memory only (`TESTING=True`).

### 3. No npm or Node.js in the Frontend
* The frontend uses **Deno 2**. Run `deno task build` inside `frontend/` instead
  of `npm run build`.

### 4. Run Verification Before Pushing
Before any `git push`, run:
1. `uv run pytest backend/tests/ -v` (All tests must pass).
2. `uv run ruff check backend desktop package.py` (Zero linter errors).
3. `.venv/Scripts/python.exe -m basedpyright` (Zero type errors).

---

## 6. Quick Cheat Sheet Table

| Task                             | Command                                       |
| :------------------------------- | :-------------------------------------------- |
| Update from GitHub               | `git pull origin master`                      |
| Check modified files             | `git status`                                  |
| View unstaged line diffs         | `git diff`                                    |
| Stage a file                     | `git add <file>`                              |
| Unstage a file                   | `git restore --staged <file>`                 |
| Discard uncommitted edits        | `git restore <file>`                          |
| Commit changes                   | `git commit -m "type(scope): description"`    |
| Push commits to GitHub           | `git push origin master`                      |
| Create and switch branch         | `git checkout -b <branch-name>`               |
| View commit history              | `git log --oneline -n 10`                     |
| Temporarily stash work           | `git stash`                                   |
| Restore stashed work             | `git stash pop`                               |
