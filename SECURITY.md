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
