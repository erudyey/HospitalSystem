# HospitalSystem Bundled Agent Skills

This repository bundles standardized agent skills under `.agents/skills/` so
that AI assistants, coding agents, and human contributors have immediate access
to specialized workflows and engineering guidelines without relying on
machine-local configurations.

---

## 1. Bundled Skills Catalog

| Skill Name            | Path                                        | Primary Purpose                                                                 | When to Use                                                                 |
| :-------------------- | :------------------------------------------ | :------------------------------------------------------------------------------ | :-------------------------------------------------------------------------- |
| **ponytail**          | `.agents/skills/ponytail/SKILL.md`          | Enforces code minimalism, YAGNI, and rejects premature abstractions.            | When adding features, refactoring, or reviewing diffs for bloat.            |
| **git-maestro**       | `.agents/skills/git-maestro/SKILL.md`       | Enforces Conventional Commits, atomic staging, and clean Git history.           | When authoring git commits, formatting messages, or managing branches.      |
| **shadcn-svelte**     | `.agents/skills/shadcn-svelte/SKILL.md`     | Guide for shadcn-svelte, bits-ui, Tailwind styling, and Svelte 5 runes.         | When creating or modifying frontend components and dialogs.                 |
| **test-master**       | `.agents/skills/test-master/SKILL.md`       | Test-driven development, boundary condition testing, and resilient fixtures.    | When writing backend pytest test cases and verifying state transitions.     |
| **surgical-patch**    | `.agents/skills/surgical-patch/SKILL.md`    | Narrow, minimal bug fixes and behavioral adjustments at the responsible layer.  | When fixing bugs or edge cases while preserving surrounding code.           |
| **verify-and-stop**   | `.agents/skills/verify-and-stop/SKILL.md`   | Rigorous quality gate proof with strict stopping discipline.                    | When validating tasks, checking gates, and completing implementation plans. |
| **security-reviewer** | `.agents/skills/security-reviewer/SKILL.md` | Security audits for authentication, password hashing, tokens, and input safety. | When touching user accounts, session middleware, or database writes.        |
| **investigate-first** | `.agents/skills/investigate-first/SKILL.md` | Evidence-ranked hypothesis diagnosis before code modification.                  | When debugging test failures or unexpected runtime behaviors.               |

---

## 2. Skill Discovery and Agent Usage

- **Automatic Discovery**: Agent systems (such as Antigravity, Claude Code,
  Windsurf, and Cursor) automatically traverse and mount workspace skills
  located in `.agents/skills/`.
- **Manual Reading**: If an agent framework does not auto-mount workspace
  skills, the agent should read the respective `SKILL.md` file using its file
  reading tool before executing related tasks.
- **Strict Repository Alignment**: All bundled skills have been audited to
  strictly follow the project's zero em/en dash policy and architecture rules.
