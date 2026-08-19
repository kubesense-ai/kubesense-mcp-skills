# Drafts

Work-in-progress skills kept in the repo but **not installable**.

The installer discovers skills by looking for `SKILL.md`. Nothing in this directory is
named `SKILL.md`, so:

- `npx skills add kubesense-ai/kubesense-mcp-skills --full-depth -y` skips it entirely
- `npx skills add ... --list --full-depth` does not show it
- `--skill <name>` cannot target it

## Contents

| File | Status |
|---|---|
| `kubesense-investigate.md` | Complete and reviewed, held back deliberately. An end-to-end incident-investigation workflow that orders alert triage → prior AI investigation → recent changes → infra failures → distributed trace → scoped logs → metrics. |

## Promoting a draft

Move it into its own top-level directory as `SKILL.md`:

```bash
mkdir kubesense-investigate
git mv drafts/kubesense-investigate.md kubesense-investigate/SKILL.md
```

Then add it back to:

- the skills table and routing table in the root `SKILL.md`
- the skills table, install command, and "Which skill do I want?" table in `README.md`
- the routing table in `kubesense-mcp/SKILL.md`
- the routing table in `kubesense-alerts/SKILL.md` (the "this alert fired" row)

Relative links inside a draft are written as if it already lived one directory below the
repo root (`../kubesense-logs/SKILL.md`), so they resolve correctly both here and after
promotion — no link edits needed.
