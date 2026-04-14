# GitHub Repository Polish — Design Spec

**Date:** 2026-04-14
**Owner:** Femi Adedayo
**Status:** Approved — ready for implementation plan

## Problem

RAG-Forge shipped v0.1.3 on 2026-04-13 with strong internals (polyglot monorepo, audit CI workflow, 6 published packages) but the GitHub presence is underdeveloped relative to comparable OSS projects (RAGAS, R2R, Cognita, Haystack, LlamaIndex). Gaps identified in the 2026-04-14 analysis:

- **Discoverability:** no repo topics, no homepage URL, default OG image
- **Trust signals:** no SECURITY.md, no CODE_OF_CONDUCT, no issue/PR templates
- **Positioning:** README is 82 lines and buries the RAG Maturity Model (the product's unique wedge) at the bottom with no comparison to peers
- **Hygiene:** 368KB `.docx` PRD at repo root (since deleted), `handoff/` untracked but visible in `git status`, `docs/prd/` is checked in but should be internal-only

The RAG Maturity Model (RMM-0 through RMM-5) and the audit-as-CI-gate workflow are genuinely differentiated but invisible to anyone landing on the repo.

## Goals

1. Make the repo discoverable via GitHub search (topics, homepage, OG image)
2. Add standard OSS trust signals (security policy, code of conduct, templates)
3. Reposition the README to lead with the RMM wedge and include honest peer comparison
4. Clean repo hygiene (remove `docs/prd/` from future commits, ignore `handoff/`)
5. Ship in two reviewable PRs so CodeRabbit can give focused feedback

## Non-Goals

- Buying a custom domain (`rag-forge.dev` not in scope)
- Setting up Discord or other community channels
- Writing marketing blog posts or launch content
- Scrubbing `docs/prd/` from git history (0 forks, 3-day-old repo, pragmatic `git rm` is sufficient)
- Enabling GitHub Sponsors (FUNDING.yml scaffold only, commented out)
- Modifying `apps/site`, `apps/site/.gitignore`, CI workflows, or CONTRIBUTING.md

## Rollout Plan

Two sequential PRs:

**PR1 — `chore/repo-polish`** (hygiene bundle, mechanical, CodeRabbit fast-pass)
**PR2 — `docs/readme-rewrite`** (subjective, depends on PR1 files existing)

PR2 branches from updated `main` after PR1 merges so it can reference new files (SECURITY.md, issue templates, OG image).

---

## PR1 — Repo Polish

### File manifest

```
.github/
├── ISSUE_TEMPLATE/
│   ├── bug_report.yml
│   ├── feature_request.yml
│   └── config.yml             (disables blank issues, links Discussions)
├── PULL_REQUEST_TEMPLATE.md
├── CODEOWNERS
├── FUNDING.yml                (commented scaffold)
└── og-image.png               (1280×640, generated)

SECURITY.md
CODE_OF_CONDUCT.md              (Contributor Covenant v2.1 verbatim)
scripts/generate-og-image.ts    (re-runnable Playwright renderer)
scripts/og-template.html        (HTML source for OG image)

REMOVED from tracking:
docs/prd/                       (git rm, added to .gitignore)

MODIFIED:
.gitignore                      (add: handoff/, docs/prd/, /*.docx)
```

### Issue templates (form-based)

**`bug_report.yml`** fields:
- Package affected (dropdown: CLI / Core / Evaluator / Observability / MCP / Templates / Docs site)
- Version (text, required)
- Node.js / Python version (text)
- OS (dropdown)
- Description (textarea, required)
- Reproduction steps (textarea, required)
- Expected vs actual behavior (textarea)
- Logs (textarea, optional, rendered as code block)

**`feature_request.yml`** fields:
- Problem statement (textarea, required)
- Proposed solution (textarea)
- Alternatives considered (textarea)
- RMM level relevance (dropdown: RMM-0 through RMM-5 / N/A)

**`config.yml`:**
```yaml
blank_issues_enabled: false
contact_links:
  - name: Discussions
    url: https://github.com/hallengray/rag-forge/discussions
    about: Ask questions, share ideas, or get help
  - name: Security vulnerabilities
    url: https://github.com/hallengray/rag-forge/security/advisories/new
    about: Report security issues privately
```

### PR template

Single `PULL_REQUEST_TEMPLATE.md` with sections: Summary, Changes, Testing done, Checklist (typecheck, lint, build, tests, docs updated if needed), Related issues.

### CODEOWNERS

```
* @hallengray
```

Single line, catches everything until contributors arrive.

### FUNDING.yml

All entries commented out. Scaffold only — ready to uncomment when Femi decides to enable sponsorship.

### SECURITY.md

Points to GitHub Private Vulnerability Reporting exclusively. Short doc:
- Supported versions table (v0.1.x currently supported)
- How to report (link to `/security/advisories/new`)
- What to expect (acknowledgement within 48h, fix timeline)
- Scope (what counts as a vulnerability vs a bug)

### CODE_OF_CONDUCT.md

Contributor Covenant v2.1 verbatim. Enforcement contact: GitHub Private Vulnerability Reporting (same channel) to avoid maintaining a separate email.

### OG image

**Design:**
- Canvas: 1280×640 PNG
- Background: `#0F172A` (slate-900)
- Text primary: white (`#FFFFFF`)
- Text secondary: slate-400 (`#94A3B8`)
- Accent: `#F97316` (orange-500) on "Forge" in wordmark + RMM arrows
- Font: Inter (loaded via Google Fonts CDN in HTML template)
- No icon (per decision C1-A)

**Layout:**
```
RAG-Forge                                                 (72px, Inter Bold)
─────────                                                 (accent underline)
Production-grade RAG pipelines                            (40px, Inter Regular)
with evaluation baked in.

RMM-0 ──▶ RMM-1 ──▶ RMM-2 ──▶ RMM-3 ──▶ RMM-4 ──▶ RMM-5  (24px, orange arrows)
Naive    Recall   Precision  Trust    Workflow  Enterprise (16px, slate-400)

rag-forge-site.vercel.app  ·  npm: @rag-forge/cli          (16px, slate-400)
```

**Generation:**
- `scripts/og-template.html` — self-contained HTML + inline CSS
- `scripts/generate-og-image.ts` — Playwright launches headless Chromium, loads file via `file://`, sets viewport to 1280×640, screenshots to `.github/og-image.png`
- Re-runnable: running the script again regenerates the PNG
- Added to `package.json` scripts as `og:generate`

### .gitignore additions

```gitignore
# Internal / working docs
handoff/
docs/prd/

# Binary product docs at repo root
/*.docx
```

Run `git rm -r --cached docs/prd/` (already in history) before the ignore takes effect.

### GitHub settings (applied via `gh` CLI post-merge)

Not version-controlled, applied manually after PR1 merges:

1. **Topics** (13): `rag`, `llm`, `rag-evaluation`, `ragas`, `llm-evaluation`, `cli`, `mcp`, `rag-pipeline`, `retrieval-augmented-generation`, `python`, `observability`, `vector-database`, `embeddings`
2. **Homepage URL:** `https://rag-forge-site.vercel.app/`
3. **Enable Private Vulnerability Reporting** (Settings → Code security)
4. **Upload OG image** as custom social preview (Settings → General → Social preview)

Commands:
```bash
gh repo edit hallengray/rag-forge \
  --homepage "https://rag-forge-site.vercel.app/" \
  --add-topic rag,llm,rag-evaluation,ragas,llm-evaluation,cli,mcp,rag-pipeline,retrieval-augmented-generation,python,observability,vector-database,embeddings

gh api -X PATCH repos/hallengray/rag-forge \
  --field security_and_analysis[private_vulnerability_reporting][status]=enabled
```

Custom social preview upload requires the GitHub web UI (no `gh` CLI equivalent as of 2026-04).

---

## PR2 — README Rewrite

### Structure (target ~250–350 lines)

1. **Hero** — name, tagline, badges row, one-sentence value prop
2. **Why RAG-Forge?** — 3-bullet problem statement, positioning sentence
3. **RAG Maturity Model** — full RMM-0→5 table (moved UP from current bottom position)
4. **Quick Start** — 3 copy-pasteable commands
5. **Installation** — CLI + Python packages (existing content, unchanged)
6. **Templates** table (existing content, unchanged)
7. **Commands** table (existing content, unchanged)
8. **Comparison** — RAG-Forge vs RAGAS vs LangChain Eval vs Giskard (honest, marks peer strengths)
9. **Architecture** — ASCII diagram of polyglot monorepo
10. **Docs / Links** — docs site, discussions, contributing, security, changelog
11. **Contributing** — link-out (existing)
12. **License** — existing

### Badges row (decision B2-B)

1. npm version — `@rag-forge/cli`
2. PyPI version — `rag-forge-core`
3. CI status — main branch
4. License — MIT
5. GitHub Discussions

Verified 200 OK before commit.

### Comparison table (decision B1 — honest)

Columns: **RAG-Forge**, **RAGAS**, **LangChain Eval**, **Giskard**
Rows: Scaffolding, Evaluation metrics, Maturity scoring, CI gate workflow, MCP server, Guardrails, Drift detection, Multi-language (TS+Py), Framework-agnostic

Marked with ✓ / ✗ / partial. Peer strengths acknowledged in a short paragraph beneath the table (e.g., "RAGAS has deeper metric research — use their metrics via `rag-forge audit --metrics ragas`").

---

## Testing & Verification

### PR1 verification

- `gh repo view` confirms topics + homepage set (post-merge step)
- `/issues/new/choose` page renders both issue templates correctly
- PR template auto-populates when opening PR itself (meta-test on the PR that adds it)
- `git log --all -- docs/prd/` shows the removal commit
- Fresh clone: `git status` shows `handoff/` ignored
- OG image validated via https://www.opengraph.xyz/url/
- Private Vulnerability Reporting toggle enabled in repo Settings
- SECURITY.md "Report a vulnerability" link works
- CI still green on branch

### PR2 verification

- GitHub web view renders markdown correctly (mobile + desktop)
- All shield.io badge URLs return 200
- All internal links resolve (`./SECURITY.md`, `./CONTRIBUTING.md`, docs site, OG image)
- Comparison table renders on GitHub mobile view
- No typos / claims that overstate current v0.1.3 features

---

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Playwright OG image generation flaky on Windows | Template is self-contained HTML; fallback to `satori` or manual screenshot if Playwright fails. Script isolated in `scripts/`. |
| `docs/prd/` removal breaks a link in `apps/site` | Grep `apps/site` for `docs/prd` references before committing. Update or keep file if found. |
| `.gitignore` alone doesn't untrack already-committed `docs/prd/` | Run `git rm -r --cached docs/prd/` in the same commit. |
| CodeRabbit nitpicks on CODE_OF_CONDUCT wording | Using Contributor Covenant v2.1 verbatim — the industry standard, don't edit. |
| Badge packages may 404 if not all published | Verify each package URL with `curl -I` before committing PR2. |
| Force-push concerns | PR1 is purely additive + one `git rm`. No force-push anywhere. |
| Comparison table draws competitor backlash | Honest framing mitigates; historically generates goodwill in OSS. |
| PR bodies accidentally include AI attribution | Per CLAUDE.md: no Co-Authored-By trailers, no "Generated with Claude" footers. |

---

## Acceptance Criteria

**PR1 is done when:**
- [ ] All files in the manifest exist in the branch
- [ ] CI passes on the branch
- [ ] CodeRabbit review addressed
- [ ] Merged to `main`
- [ ] Topics, homepage URL, PVR, and OG image applied via GitHub settings
- [ ] Fresh clone shows `handoff/` and `docs/prd/` ignored

**PR2 is done when:**
- [ ] README matches the structure above
- [ ] All badges resolve
- [ ] All internal links resolve
- [ ] Comparison table is accurate and honest
- [ ] CodeRabbit review addressed
- [ ] Merged to `main`

**Overall done when:**
- [ ] Pasting the repo URL into a social preview validator shows the new OG image
- [ ] `github.com/hallengray/rag-forge` sidebar shows topics, homepage link, and security policy
- [ ] Issue creation flow offers the two templates
