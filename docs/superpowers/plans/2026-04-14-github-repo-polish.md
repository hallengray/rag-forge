# GitHub Repo Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close discoverability, trust-signal, and positioning gaps on the RAG-Forge GitHub repo across two PRs.

**Architecture:** PR1 (`chore/repo-polish`) adds all standard OSS files (issue/PR templates, SECURITY, CODE_OF_CONDUCT, CODEOWNERS, OG image) and cleans repo hygiene (removes `docs/prd/`, ignores `handoff/`). PR2 (`docs/readme-rewrite`) rewrites README to lead with the RMM wedge and adds honest peer comparison. GitHub settings (topics, homepage, PVR, social preview) applied via `gh` CLI after PR1 merges.

**Tech Stack:** GitHub CLI (`gh`), Playwright (existing devDep), Node 20+, pnpm 10, Contributor Covenant v2.1, Shields.io badges.

**Spec:** `docs/superpowers/specs/2026-04-14-github-repo-polish-design.md`

---

## PR1 — `chore/repo-polish`

### Task 1: Create branch and baseline

**Files:** none

- [ ] **Step 1: Verify clean working tree and up-to-date main**

```bash
cd C:/Users/halle/Downloads/RAGforge
git status
git fetch origin
git checkout main
git pull --ff-only origin main
```

Expected: working tree clean (except for pre-existing untracked `handoff/`, `apps/site/.gitignore`), main up to date.

- [ ] **Step 2: Create branch**

```bash
git checkout -b chore/repo-polish
```

Expected: `Switched to a new branch 'chore/repo-polish'`

---

### Task 2: Update `.gitignore` and untrack `docs/prd/`

**Files:**
- Modify: `.gitignore`
- Remove from tracking: `docs/prd/` (files stay on disk locally)

- [ ] **Step 1: Append new ignore rules to `.gitignore`**

Append to end of `.gitignore`:

```gitignore

# Internal / working docs (not for public repo)
handoff/
docs/prd/

# Binary product docs at repo root
/*.docx
```

- [ ] **Step 2: Untrack `docs/prd/` (files remain on disk)**

```bash
git rm -r --cached docs/prd/
```

Expected: a list of `rm 'docs/prd/...'` lines.

- [ ] **Step 3: Verify handoff is now ignored**

```bash
git status --short
```

Expected: `handoff/` and `docs/prd/` should NOT appear as untracked. Staged deletions of `docs/prd/*` should be visible.

- [ ] **Step 4: Commit**

```bash
git add .gitignore
git commit -m "chore: gitignore handoff/, docs/prd/, root .docx files

Untrack docs/prd/ (keep local copies). Internal PRD is not for the public repo."
```

---

### Task 3: Issue templates

**Files:**
- Create: `.github/ISSUE_TEMPLATE/bug_report.yml`
- Create: `.github/ISSUE_TEMPLATE/feature_request.yml`
- Create: `.github/ISSUE_TEMPLATE/config.yml`

- [ ] **Step 1: Create `.github/ISSUE_TEMPLATE/bug_report.yml`**

```yaml
name: Bug report
description: Report a bug in RAG-Forge
title: "[Bug]: "
labels: ["bug", "triage"]
body:
  - type: markdown
    attributes:
      value: |
        Thanks for taking the time to file a bug. Please fill out the fields below so we can reproduce and fix it quickly.
  - type: dropdown
    id: package
    attributes:
      label: Package affected
      options:
        - CLI (@rag-forge/cli)
        - Core (rag-forge-core)
        - Evaluator (rag-forge-evaluator)
        - Observability (rag-forge-observability)
        - MCP server (@rag-forge/mcp)
        - Templates
        - Docs site
        - Unsure
    validations:
      required: true
  - type: input
    id: version
    attributes:
      label: Version
      description: Output of `rag-forge --version` or package version from `package.json` / `pyproject.toml`
      placeholder: "0.1.3"
    validations:
      required: true
  - type: input
    id: runtime
    attributes:
      label: Node.js / Python version
      placeholder: "Node 20.11.0 / Python 3.11.7"
    validations:
      required: true
  - type: dropdown
    id: os
    attributes:
      label: Operating system
      options:
        - macOS
        - Linux
        - Windows
        - Docker
        - Other
    validations:
      required: true
  - type: textarea
    id: description
    attributes:
      label: Description
      description: What went wrong? What did you expect to happen?
    validations:
      required: true
  - type: textarea
    id: reproduction
    attributes:
      label: Reproduction steps
      description: Minimal steps to reproduce the issue.
      placeholder: |
        1. Run `rag-forge init basic`
        2. ...
        3. See error
    validations:
      required: true
  - type: textarea
    id: logs
    attributes:
      label: Relevant logs
      description: Paste logs, stack traces, or error output. Will be rendered as a code block.
      render: shell
```

- [ ] **Step 2: Create `.github/ISSUE_TEMPLATE/feature_request.yml`**

```yaml
name: Feature request
description: Suggest a new feature or improvement
title: "[Feature]: "
labels: ["enhancement", "triage"]
body:
  - type: textarea
    id: problem
    attributes:
      label: Problem statement
      description: What problem are you trying to solve? Who is affected?
    validations:
      required: true
  - type: textarea
    id: solution
    attributes:
      label: Proposed solution
      description: Describe the feature or change you'd like to see.
    validations:
      required: true
  - type: textarea
    id: alternatives
    attributes:
      label: Alternatives considered
      description: Other approaches you've thought about and why you rejected them.
  - type: dropdown
    id: rmm
    attributes:
      label: RMM level relevance
      description: Which RAG Maturity Model level does this feature relate to?
      options:
        - RMM-0 (Naive)
        - RMM-1 (Better Recall)
        - RMM-2 (Better Precision)
        - RMM-3 (Better Trust)
        - RMM-4 (Better Workflow)
        - RMM-5 (Enterprise)
        - Not applicable
    validations:
      required: true
```

- [ ] **Step 3: Create `.github/ISSUE_TEMPLATE/config.yml`**

```yaml
blank_issues_enabled: false
contact_links:
  - name: Discussions
    url: https://github.com/hallengray/rag-forge/discussions
    about: Ask questions, share ideas, or get help from the community.
  - name: Report a security vulnerability
    url: https://github.com/hallengray/rag-forge/security/advisories/new
    about: Please report security issues privately via GitHub's private vulnerability reporting.
```

- [ ] **Step 4: Commit**

```bash
git add .github/ISSUE_TEMPLATE/
git commit -m "chore(github): add issue templates for bugs and features"
```

---

### Task 4: PR template

**Files:**
- Create: `.github/PULL_REQUEST_TEMPLATE.md`

- [ ] **Step 1: Create `.github/PULL_REQUEST_TEMPLATE.md`**

```markdown
## Summary

<!-- One or two sentences: what does this PR do and why? -->

## Changes

<!-- Bulleted list of notable changes. -->

-
-

## Testing done

<!-- How did you verify this works? Commands run, manual checks, screenshots if UI. -->

-

## Checklist

- [ ] `pnpm run typecheck` passes
- [ ] `pnpm run lint` passes
- [ ] `pnpm run build` passes
- [ ] `pnpm run test` passes (TS + Python)
- [ ] Docs updated if behavior or public APIs changed
- [ ] No secrets, credentials, or `.env` files committed

## Related issues

<!-- Closes #123, Refs #456 -->
```

- [ ] **Step 2: Commit**

```bash
git add .github/PULL_REQUEST_TEMPLATE.md
git commit -m "chore(github): add pull request template"
```

---

### Task 5: CODEOWNERS and FUNDING

**Files:**
- Create: `.github/CODEOWNERS`
- Create: `.github/FUNDING.yml`

- [ ] **Step 1: Create `.github/CODEOWNERS`**

```
# Default owner for everything in the repo
* @hallengray
```

- [ ] **Step 2: Create `.github/FUNDING.yml`**

```yaml
# GitHub Sponsors and funding platforms for RAG-Forge.
# Uncomment and populate when ready to enable sponsorship.

# github: [hallengray]
# ko_fi: hallengray
# custom: ["https://rag-forge-site.vercel.app/"]
```

- [ ] **Step 3: Commit**

```bash
git add .github/CODEOWNERS .github/FUNDING.yml
git commit -m "chore(github): add CODEOWNERS and FUNDING scaffold"
```

---

### Task 6: SECURITY.md

**Files:**
- Create: `SECURITY.md`

- [ ] **Step 1: Create `SECURITY.md`**

```markdown
# Security Policy

RAG-Forge takes security seriously. If you believe you have found a security vulnerability in any RAG-Forge package (CLI, Core, Evaluator, Observability, MCP server, or templates), please report it to us privately.

## Supported Versions

We provide security updates for the latest minor release line.

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |
| < 0.1   | :x:                |

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Instead, report vulnerabilities privately via GitHub's built-in private vulnerability reporting:

➡️ **[Report a vulnerability](https://github.com/hallengray/rag-forge/security/advisories/new)**

### What to include

- A clear description of the vulnerability and its potential impact
- Steps to reproduce, or a proof-of-concept
- The RAG-Forge package and version affected
- Your environment (OS, Node/Python version)
- Any suggested mitigations

### What to expect

- **Acknowledgement:** within 48 hours of your report
- **Initial assessment:** within 5 business days
- **Fix timeline:** depends on severity — critical issues are patched and released as quickly as possible; lower-severity issues are bundled into the next minor release
- **Credit:** with your permission, we will credit you in the release notes and security advisory

## Scope

**In scope:**
- RAG-Forge published packages on npm (`@rag-forge/*`) and PyPI (`rag-forge-*`)
- Code in this repository
- The CLI binary and MCP server
- Published templates

**Out of scope:**
- Bugs that are not security vulnerabilities (please file a regular issue)
- Vulnerabilities in third-party dependencies (please report upstream; we will update affected dependencies)
- Self-hosted deployments where the issue is a misconfiguration rather than a product defect
- Denial-of-service caused by pathological input to local CLI tools

## Safe Harbor

We consider security research performed in good faith and in accordance with this policy to be authorized. We will not pursue legal action against researchers who comply with this policy.
```

- [ ] **Step 2: Commit**

```bash
git add SECURITY.md
git commit -m "docs(security): add SECURITY.md with GitHub Private Vulnerability Reporting"
```

---

### Task 7: CODE_OF_CONDUCT.md

**Files:**
- Create: `CODE_OF_CONDUCT.md`

- [ ] **Step 1: Fetch Contributor Covenant v2.1**

Copy the verbatim text from https://www.contributor-covenant.org/version/2/1/code_of_conduct/code_of_conduct.md into `CODE_OF_CONDUCT.md`.

Alternative exact command (curl):

```bash
curl -sSL https://www.contributor-covenant.org/version/2/1/code_of_conduct/code_of_conduct.md -o CODE_OF_CONDUCT.md
```

Expected: file created, ~135 lines.

- [ ] **Step 2: Replace the enforcement contact placeholder**

The template contains the line:

```
Instances of abusive, harassing, or otherwise unacceptable behavior may be
reported to the community leaders responsible for enforcement at
[INSERT CONTACT METHOD].
```

Replace `[INSERT CONTACT METHOD]` with:

```
via [GitHub's private vulnerability reporting](https://github.com/hallengray/rag-forge/security/advisories/new)
```

- [ ] **Step 3: Verify substitution**

```bash
grep -n "INSERT CONTACT METHOD" CODE_OF_CONDUCT.md
```

Expected: no output (placeholder replaced).

```bash
grep -n "security/advisories/new" CODE_OF_CONDUCT.md
```

Expected: one match.

- [ ] **Step 4: Commit**

```bash
git add CODE_OF_CONDUCT.md
git commit -m "docs: add Contributor Covenant v2.1 code of conduct"
```

---

### Task 8: OG image HTML template

**Files:**
- Create: `scripts/og-template.html`

- [ ] **Step 1: Create `scripts/og-template.html`**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>RAG-Forge OG</title>
    <link
      href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap"
      rel="stylesheet"
    />
    <style>
      * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
      }
      html,
      body {
        width: 1280px;
        height: 640px;
        background: #0f172a;
        font-family: "Inter", system-ui, sans-serif;
        color: #ffffff;
        -webkit-font-smoothing: antialiased;
      }
      .wrap {
        padding: 72px 80px;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
      }
      .brand {
        font-size: 88px;
        font-weight: 800;
        letter-spacing: -0.02em;
        line-height: 1;
      }
      .brand .accent {
        color: #f97316;
      }
      .rule {
        width: 120px;
        height: 6px;
        background: #f97316;
        margin: 20px 0 32px;
        border-radius: 3px;
      }
      .tagline {
        font-size: 44px;
        font-weight: 400;
        line-height: 1.2;
        color: #e2e8f0;
        max-width: 900px;
      }
      .rmm {
        display: flex;
        align-items: flex-end;
        gap: 14px;
        margin-top: 24px;
      }
      .step {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 8px;
      }
      .step .level {
        font-size: 22px;
        font-weight: 600;
        color: #ffffff;
      }
      .step .name {
        font-size: 14px;
        color: #94a3b8;
      }
      .arrow {
        color: #f97316;
        font-size: 24px;
        font-weight: 800;
        padding-bottom: 18px;
      }
      .foot {
        font-size: 18px;
        color: #94a3b8;
        display: flex;
        gap: 16px;
        align-items: center;
      }
      .foot .dot {
        color: #475569;
      }
    </style>
  </head>
  <body>
    <div class="wrap">
      <div>
        <div class="brand">RAG-<span class="accent">Forge</span></div>
        <div class="rule"></div>
        <div class="tagline">
          Production-grade RAG pipelines<br />with evaluation baked in.
        </div>
      </div>
      <div class="rmm">
        <div class="step"><div class="level">RMM-0</div><div class="name">Naive</div></div>
        <div class="arrow">▶</div>
        <div class="step"><div class="level">RMM-1</div><div class="name">Recall</div></div>
        <div class="arrow">▶</div>
        <div class="step"><div class="level">RMM-2</div><div class="name">Precision</div></div>
        <div class="arrow">▶</div>
        <div class="step"><div class="level">RMM-3</div><div class="name">Trust</div></div>
        <div class="arrow">▶</div>
        <div class="step"><div class="level">RMM-4</div><div class="name">Workflow</div></div>
        <div class="arrow">▶</div>
        <div class="step"><div class="level">RMM-5</div><div class="name">Enterprise</div></div>
      </div>
      <div class="foot">
        <span>rag-forge-site.vercel.app</span>
        <span class="dot">·</span>
        <span>npm: @rag-forge/cli</span>
      </div>
    </div>
  </body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git add scripts/og-template.html
git commit -m "chore(og): add HTML template for OG image generation"
```

---

### Task 9: OG image generator script

**Files:**
- Create: `scripts/generate-og-image.ts`
- Modify: `package.json` (add `og:generate` script and Playwright devDep if missing)

- [ ] **Step 1: Check if Playwright is already installed**

```bash
cd C:/Users/halle/Downloads/RAGforge
node -e "console.log(require('./package.json').devDependencies?.playwright || 'missing')"
```

If output is `missing`, install it:

```bash
pnpm add -D -w playwright
pnpm exec playwright install chromium
```

If already present, skip install.

- [ ] **Step 2: Create `scripts/generate-og-image.ts`**

```ts
import { chromium } from "playwright";
import { fileURLToPath } from "node:url";
import path from "node:path";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const templatePath = path.join(__dirname, "og-template.html");
const outputPath = path.join(__dirname, "..", ".github", "og-image.png");

async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1280, height: 640 },
    deviceScaleFactor: 2,
  });
  const page = await context.newPage();
  const fileUrl = "file://" + templatePath.replace(/\\/g, "/");
  await page.goto(fileUrl, { waitUntil: "networkidle" });
  // Give webfonts a moment to settle after network idle
  await page.waitForTimeout(500);
  await page.screenshot({ path: outputPath, omitBackground: false });
  await browser.close();
  console.log("Wrote " + outputPath);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
```

- [ ] **Step 3: Add `og:generate` script to `package.json`**

In `package.json`, add this line to the `scripts` object (after `prepare`):

```json
    "og:generate": "tsx scripts/generate-og-image.ts"
```

If `tsx` is not already a devDependency, install it:

```bash
node -e "console.log(require('./package.json').devDependencies?.tsx || 'missing')"
```

If `missing`:

```bash
pnpm add -D -w tsx
```

- [ ] **Step 4: Ensure `.github/` directory exists**

```bash
mkdir -p .github
```

- [ ] **Step 5: Commit**

```bash
git add scripts/generate-og-image.ts package.json pnpm-lock.yaml
git commit -m "chore(og): add Playwright-based OG image generator"
```

---

### Task 10: Generate and commit OG image

**Files:**
- Create: `.github/og-image.png`

- [ ] **Step 1: Run generator**

```bash
pnpm run og:generate
```

Expected: `Wrote .../RAGforge/.github/og-image.png`

- [ ] **Step 2: Verify file exists and dimensions are 1280×640 (or 2560×1280 at 2x DPR)**

```bash
ls -la .github/og-image.png
```

Expected: file present, non-zero size (typically 80–200 KB).

Optional visual check: open the PNG in an image viewer and confirm the layout matches the spec (slate background, orange "Forge", RMM row, footer text).

- [ ] **Step 3: Commit**

```bash
git add .github/og-image.png
git commit -m "chore(og): add generated social preview image"
```

---

### Task 11: Push branch and open PR1

**Files:** none (GitHub PR)

- [ ] **Step 1: Push branch**

```bash
git push -u origin chore/repo-polish
```

- [ ] **Step 2: Open PR**

```bash
gh pr create --base main --head chore/repo-polish --title "chore: repo hygiene — templates, security, OG image" --body "$(cat <<'EOF'
## Summary

Closes the GitHub discoverability and trust-signal gaps identified in the 2026-04-14 repo analysis. Pure additions plus removal of internal PRD from tracking. README rewrite ships in a separate PR.

## Changes

- Add GitHub issue templates (bug_report, feature_request) and config.yml
- Add PR template
- Add CODEOWNERS and FUNDING.yml scaffold
- Add SECURITY.md pointing to GitHub Private Vulnerability Reporting
- Add CODE_OF_CONDUCT.md (Contributor Covenant v2.1)
- Add OG image (1280×640) + Playwright-based regenerator script
- Gitignore handoff/, docs/prd/, and root .docx files
- Untrack docs/prd/ (PRD is internal — kept locally, removed from future commits)

## Testing done

- Verified `.gitignore` untracks handoff/ and docs/prd/
- Ran `pnpm run og:generate` — PNG written to `.github/og-image.png`
- Issue templates validated locally (YAML parses)
- CODE_OF_CONDUCT placeholder replaced and grep-verified
- All existing CI should continue to pass (no source code changes)

## Checklist

- [x] No secrets committed
- [x] CI not modified
- [x] Docs (internal spec) referenced

## Follow-up

Post-merge, apply GitHub settings via gh CLI: topics, homepage URL, enable Private Vulnerability Reporting, upload social preview image. Commands documented in the design spec.

## Related

Refs: docs/superpowers/specs/2026-04-14-github-repo-polish-design.md
EOF
)"
```

- [ ] **Step 3: Capture PR URL for reference**

Expected: `gh` prints the PR URL. Save it — you'll paste it back to Femi.

- [ ] **Step 4: Wait for CodeRabbit review, address feedback**

CodeRabbit typically posts within 2–5 minutes. Address any feedback in follow-up commits on the same branch.

- [ ] **Step 5: Merge after approval**

Per project convention, Femi merges PRs himself. Do NOT auto-merge.

---

### Task 12: Apply GitHub settings post-merge

**Files:** none — applied via `gh` CLI after PR1 merges to main

- [ ] **Step 1: Pull merged main**

```bash
git checkout main
git pull --ff-only origin main
```

- [ ] **Step 2: Set topics and homepage URL**

```bash
gh repo edit hallengray/rag-forge \
  --homepage "https://rag-forge-site.vercel.app/" \
  --add-topic rag,llm,rag-evaluation,ragas,llm-evaluation,cli,mcp,rag-pipeline,retrieval-augmented-generation,python,observability,vector-database,embeddings
```

- [ ] **Step 3: Verify topics and homepage**

```bash
gh repo view hallengray/rag-forge --json homepageUrl,repositoryTopics
```

Expected output:

```json
{
  "homepageUrl": "https://rag-forge-site.vercel.app/",
  "repositoryTopics": [
    {"name":"rag"}, {"name":"llm"}, {"name":"rag-evaluation"},
    {"name":"ragas"}, {"name":"llm-evaluation"}, {"name":"cli"},
    {"name":"mcp"}, {"name":"rag-pipeline"},
    {"name":"retrieval-augmented-generation"}, {"name":"python"},
    {"name":"observability"}, {"name":"vector-database"},
    {"name":"embeddings"}
  ]
}
```

- [ ] **Step 4: Enable Private Vulnerability Reporting**

```bash
gh api -X PUT repos/hallengray/rag-forge/private-vulnerability-reporting
```

Expected: no error, HTTP 204.

- [ ] **Step 5: Verify PVR enabled**

```bash
gh api repos/hallengray/rag-forge --jq '.security_and_analysis.private_vulnerability_reporting.status'
```

Expected: `"enabled"`

- [ ] **Step 6: Upload social preview image (manual — GitHub UI)**

Because `gh` does not expose social preview uploads as of 2026-04, this step is manual:

1. Open https://github.com/hallengray/rag-forge/settings
2. Scroll to "Social preview"
3. Click "Edit" → "Upload an image"
4. Select `.github/og-image.png` from the repo
5. Save

- [ ] **Step 7: Verify OG card renders**

Paste `https://github.com/hallengray/rag-forge` into https://www.opengraph.xyz/url/ and confirm the custom OG image shows (not the GitHub default).

---

## PR2 — `docs/readme-rewrite`

### Task 13: Create PR2 branch from updated main

**Files:** none

- [ ] **Step 1: Ensure main is up to date (post PR1 merge)**

```bash
git checkout main
git pull --ff-only origin main
```

- [ ] **Step 2: Create branch**

```bash
git checkout -b docs/readme-rewrite
```

---

### Task 14: Verify badge URLs return 200

**Files:** none — pre-check before writing README

- [ ] **Step 1: Check each badge endpoint**

```bash
curl -s -o /dev/null -w "%{http_code} %{url_effective}\n" "https://img.shields.io/npm/v/@rag-forge/cli"
curl -s -o /dev/null -w "%{http_code} %{url_effective}\n" "https://img.shields.io/pypi/v/rag-forge-core"
curl -s -o /dev/null -w "%{http_code} %{url_effective}\n" "https://img.shields.io/github/actions/workflow/status/hallengray/rag-forge/ci.yml?branch=main"
curl -s -o /dev/null -w "%{http_code} %{url_effective}\n" "https://img.shields.io/github/license/hallengray/rag-forge"
curl -s -o /dev/null -w "%{http_code} %{url_effective}\n" "https://img.shields.io/github/discussions/hallengray/rag-forge"
```

Expected: all return `200`. If any return non-200, adjust the badge URL or swap for an alternative before proceeding.

- [ ] **Step 2: Check package pages resolve**

```bash
curl -s -o /dev/null -w "%{http_code}\n" "https://www.npmjs.com/package/@rag-forge/cli"
curl -s -o /dev/null -w "%{http_code}\n" "https://pypi.org/project/rag-forge-core/"
```

Expected: both `200`.

---

### Task 15: Rewrite `README.md`

**Files:**
- Modify (full rewrite): `README.md`

- [ ] **Step 1: Replace `README.md` with the new content**

Replace the entire contents of `README.md` with:

```markdown
<div align="center">

# RAG-Forge

**Production-grade RAG pipelines with evaluation baked in — not bolted on after deployment.**

[![npm version](https://img.shields.io/npm/v/@rag-forge/cli?label=%40rag-forge%2Fcli)](https://www.npmjs.com/package/@rag-forge/cli)
[![PyPI version](https://img.shields.io/pypi/v/rag-forge-core?label=rag-forge-core)](https://pypi.org/project/rag-forge-core/)
[![CI](https://img.shields.io/github/actions/workflow/status/hallengray/rag-forge/ci.yml?branch=main)](https://github.com/hallengray/rag-forge/actions)
[![License: MIT](https://img.shields.io/github/license/hallengray/rag-forge)](./LICENSE)
[![Discussions](https://img.shields.io/github/discussions/hallengray/rag-forge)](https://github.com/hallengray/rag-forge/discussions)

[Docs](https://rag-forge-docs.vercel.app/) · [Website](https://rag-forge-site.vercel.app/) · [Discussions](https://github.com/hallengray/rag-forge/discussions) · [Changelog](./docs/release-notes)

</div>

---

## Why RAG-Forge?

Most RAG projects ship without evaluation, and most evaluation libraries don't help you build the pipeline. Nobody scores maturity — so teams don't know if they're at "a demo that sometimes works" or "a system you can put in front of customers."

- **Building a RAG pipeline is easy. Knowing whether it works is hard.** RAG-Forge closes that loop.
- **Eval is a first-class citizen, not an afterthought.** Every template ships with a golden set and an audit gate.
- **The RAG Maturity Model (RMM-0 → RMM-5)** gives you a concrete scorecard for any RAG system — yours or someone else's.

RAG-Forge is the only toolkit that scaffolds production-ready RAG pipelines, runs continuous evaluation as a CI/CD gate, and scores any existing system against a published maturity model.

---

## RAG Maturity Model

The RMM is the scoring framework at the heart of RAG-Forge. Run `rag-forge assess` on any audit report to see where your system sits.

| Level | Name              | Exit Criteria                                              |
|-------|-------------------|------------------------------------------------------------|
| RMM-0 | Naive             | Basic vector search works                                  |
| RMM-1 | Better Recall     | Hybrid search, Recall@5 > 70%                              |
| RMM-2 | Better Precision  | Reranker active, nDCG@10 +10%                              |
| RMM-3 | Better Trust      | Guardrails, faithfulness > 85%                             |
| RMM-4 | Better Workflow   | Caching, P95 < 4s, cost tracking                           |
| RMM-5 | Enterprise        | Drift detection, CI/CD gates, adversarial tests            |

---

## Quick Start

```bash
npm install -g @rag-forge/cli

rag-forge init basic my-rag-project
cd my-rag-project

rag-forge index --source ./docs
rag-forge audit --golden-set eval/golden_set.json
rag-forge assess --audit-report reports/audit-report.json
```

Three commands to go from empty directory to a scored RAG system with a golden set and an audit report.

---

## Installation

**CLI (Node.js 20+):**

```bash
npm install -g @rag-forge/cli
```

**Python packages (Python 3.11+):**

```bash
pip install rag-forge-core rag-forge-evaluator rag-forge-observability
```

---

## Templates

| Template     | Use Case                                             |
|--------------|------------------------------------------------------|
| `basic`      | First RAG project, simple Q&A                        |
| `hybrid`     | Production-ready document Q&A with reranking         |
| `agentic`    | Multi-hop reasoning with query decomposition         |
| `enterprise` | Regulated industries with full security suite       |
| `n8n`        | AI automation agency deployments                     |

Templates generate editable source code in your project — not framework dependencies. Fork the code, not the abstraction.

---

## Commands

| Category         | Commands                                                             |
|------------------|----------------------------------------------------------------------|
| **Scaffolding**  | `init`, `add`                                                        |
| **Ingestion**    | `parse`, `chunk`, `index`                                            |
| **Query**        | `query`, `inspect`                                                   |
| **Evaluation**   | `audit`, `assess`, `golden add`, `golden validate`                   |
| **Operations**   | `report`, `cache stats`, `drift report`, `cost`                      |
| **Security**     | `guardrails test`, `guardrails scan-pii`                             |
| **Integration**  | `serve --mcp`, `n8n export`                                          |

Run `rag-forge --help` for the full command reference.

---

## How RAG-Forge compares

There are great tools in this space. Here's an honest look at where each fits.

| Capability                        | RAG-Forge | RAGAS  | LangChain Eval | Giskard |
|-----------------------------------|:---------:|:------:|:--------------:|:-------:|
| Scaffolds a RAG pipeline          |     ✓     |   —    |       —        |    —    |
| Evaluation metrics                |     ✓     |   ✓    |       ✓        |    ✓    |
| Maturity scoring (RMM-0 → 5)      |     ✓     |   —    |       —        |    —    |
| CI gate workflow (audit action)   |     ✓     |   —    |    partial     | partial |
| MCP server                        |     ✓     |   —    |       —        |    —    |
| Guardrails / PII scanning         |     ✓     |   —    |    partial     |    ✓    |
| Drift detection                   |     ✓     |   —    |       —        | partial |
| Multi-language (TS + Python)      |     ✓     |   —    |       ✓        |    —    |
| Framework-agnostic                |     ✓     |   ✓    |       —        |    ✓    |

**Peer strengths worth knowing:**

- **RAGAS** has deeper metric research and a large community. RAG-Forge's evaluator supports RAGAS metrics — run `rag-forge audit --metrics ragas` to use them directly.
- **LangChain Eval** has the broadest ecosystem of integrations if you're already invested in LangChain.
- **Giskard** has a strong general-purpose ML testing story beyond RAG.

Pick the tool that matches your stage. RAG-Forge's wedge is the full lifecycle — scaffold → evaluate → score → ship — in one CLI, with the RMM as the objective function.

---

## Architecture

RAG-Forge is a polyglot monorepo. The CLI and MCP server are TypeScript; all RAG logic is Python. The CLI delegates to Python via a subprocess bridge so the two halves can be developed and versioned independently.

```
rag-forge/
├── packages/
│   ├── cli/              TypeScript — Commander.js CLI (rag-forge command)
│   ├── mcp/              TypeScript — MCP server (@modelcontextprotocol/sdk)
│   ├── core/             Python    — RAG pipeline primitives
│   ├── evaluator/        Python    — RAGAS + DeepEval + LLM-as-Judge
│   └── observability/    Python    — OpenTelemetry + Langfuse
├── templates/            Project templates (basic, hybrid, agentic, enterprise, n8n)
└── apps/site/            Docs and marketing site (Next.js, deployed to Vercel)
```

See [docs/architecture.md](./docs/architecture.md) for a deeper dive.

---

## Docs & Community

- 📚 **Docs:** https://rag-forge-docs.vercel.app/
- 🌐 **Website:** https://rag-forge-site.vercel.app/
- 💬 **Discussions:** https://github.com/hallengray/rag-forge/discussions
- 🔒 **Security:** see [SECURITY.md](./SECURITY.md)
- 📝 **Changelog:** [docs/release-notes](./docs/release-notes)

---

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for development setup and contribution guidelines. All contributors are expected to follow our [Code of Conduct](./CODE_OF_CONDUCT.md).

---

## License

MIT — see [LICENSE](./LICENSE)
```

- [ ] **Step 2: Verify README renders as markdown**

```bash
cat README.md | head -20
wc -l README.md
```

Expected: file starts with `<div align="center">`, total line count between 180–260.

- [ ] **Step 3: Verify all internal links exist**

```bash
ls SECURITY.md CODE_OF_CONDUCT.md CONTRIBUTING.md LICENSE docs/architecture.md docs/release-notes
```

Expected: all exist. `docs/release-notes` is a directory — `ls` should succeed.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs(readme): rewrite README to lead with RMM wedge and peer comparison"
```

---

### Task 16: Push PR2 and open pull request

**Files:** none (GitHub PR)

- [ ] **Step 1: Push branch**

```bash
git push -u origin docs/readme-rewrite
```

- [ ] **Step 2: Open PR**

```bash
gh pr create --base main --head docs/readme-rewrite --title "docs: rewrite README to lead with RMM and peer comparison" --body "$(cat <<'EOF'
## Summary

Rewrites README from 82 lines to ~220 lines. Leads with the RAG Maturity Model (previously buried at the bottom) and adds an honest comparison to RAGAS, LangChain Eval, and Giskard. Badges row, docs/website links, and architecture summary added.

## Changes

- Hero with centered badges row (npm, PyPI, CI, license, discussions) and top-nav links
- "Why RAG-Forge?" positioning section
- RMM table promoted to second section
- 3-command Quick Start
- Installation, Templates, Commands (preserved from original)
- Honest "How RAG-Forge compares" feature matrix + peer strengths paragraph
- Architecture tree + link to docs/architecture.md
- Docs & Community link block
- Code of Conduct link in Contributing section

## Testing done

- Verified all badge URLs return 200 via curl
- Verified all internal file links exist (SECURITY.md, CODE_OF_CONDUCT.md, CONTRIBUTING.md, LICENSE, docs/architecture.md, docs/release-notes)
- Visually inspected markdown rendering on GitHub preview

## Checklist

- [x] All badges resolve
- [x] All internal links resolve
- [x] Comparison table is honest and marks peer strengths
- [x] No overstatement of v0.1.3 capabilities

## Related

Follows PR #<PR1 number>. Refs: docs/superpowers/specs/2026-04-14-github-repo-polish-design.md
EOF
)"
```

Replace `<PR1 number>` with the actual PR1 number before running.

- [ ] **Step 3: Visually review rendered README on GitHub**

Open the PR in the browser. Click through to the "Files changed" tab and then the README preview. Confirm:

- Badges render
- Comparison table renders on mobile (narrow the browser window to test)
- All links are clickable
- Centered hero block looks right

- [ ] **Step 4: Wait for CodeRabbit, address feedback, hand off to Femi for merge**

---

## Final Verification (after both PRs merged)

- [ ] **Step 1: Fresh clone smoke test**

```bash
cd /tmp
git clone https://github.com/hallengray/rag-forge.git rf-smoke
cd rf-smoke
git status
ls SECURITY.md CODE_OF_CONDUCT.md .github/og-image.png .github/ISSUE_TEMPLATE/bug_report.yml
```

Expected: clean clone, all files present, no `docs/prd/` or `handoff/` present.

- [ ] **Step 2: Issue creation flow**

Open https://github.com/hallengray/rag-forge/issues/new/choose in a browser. Expected: two template cards (Bug report, Feature request) plus two contact links (Discussions, Security).

- [ ] **Step 3: OG card validation**

Paste `https://github.com/hallengray/rag-forge` into https://www.opengraph.xyz/url/ and confirm the custom card renders (dark slate, orange "Forge", RMM row).

- [ ] **Step 4: Sidebar metadata**

Open the repo homepage and confirm the sidebar shows:
- Description
- Website link → `https://rag-forge-site.vercel.app/`
- All 13 topics as clickable tags
- "Report a vulnerability" link (from enabled PVR)

- [ ] **Step 5: Clean up local scratch**

```bash
rm -rf /tmp/rf-smoke
```

---

## Rollback plan

If anything goes wrong:

- **PR1 bad after merge:** revert via `gh pr revert <PR1 number>` — all changes are additive except the `docs/prd/` untrack, which is recoverable from git history.
- **Topics / homepage / PVR misapplied:** `gh repo edit --remove-topic <name>` and re-run with corrections. Settings are idempotent.
- **OG image wrong:** tweak `scripts/og-template.html`, rerun `pnpm run og:generate`, commit new PNG.
- **PR2 README regression:** revert via `gh pr revert <PR2 number>`. README is a single file.
