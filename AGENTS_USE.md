# AGENTS_USE.md — Template & Instructions
<!-- agent documentation: use cases, implementation details, observability evidence, and safety measures (reference: https://docs.anthropic.com/en/docs/agents-use-md) -->


Every team must include an `AGENTS_USE.md` file at the root of their repository. This file documents your agent implementation in a standardized format so evaluators can understand your solution without needing to run it.

The template is attached below this message. Copy it into your repo and fill in each section.

**The provided information must be concise and text-based, unless explicitly required and except for Sections 6 (Observability) and 7 (Security). These should provide evidence  — screenshots, log samples, trace exports, or test results. Descriptions alone are not sufficient.**

**The file covers 9 sections:**
1. Agent Overview — name, purpose, tech stack
2. Agents & Capabilities — structured description of each agent/sub-agent
3. Architecture & Orchestration — system design, data flow, error handling (include a diagram)
4. Context Engineering — how your agents source, filter, and manage context
5. Use Cases — step-by-step walkthroughs from trigger to resolution
6. Observability — logging, tracing, metrics
7. Security & Guardrails — prompt injection defense, input validation, tool safety
8. Scalability — capacity, approach, bottlenecks
9. Lessons Learned — what worked, what you'd change, key trade-offs

**Remember:** Sections 6 (Observability) and 7 (Security) require **actual evidence** — screenshots, log samples, trace exports, or test results. Descriptions alone are not sufficient.

---

---
<!-- The ones below are from AI's suggestion (not sure if the top from the hackathon is an actual example. The link shared in deliverables.md shows page not found (https://docs.anthropic.com/en/docs/agents-use-md)  -->
---

# AGENTS-USE.md

This document defines how **AI agents** (LLMs, copilots, automation agents, or bots) are allowed and expected to interact with this repository.

---

## Purpose

This file exists to:
- Clarify what agents **may and may not do**
- Reduce unsafe or unintended changes
- Provide guidance for automated contributions
- Improve consistency and reviewability of agent-generated output

---

## Scope

Applies to:
- Code assistants (Copilot, ChatGPT, Gemini, etc.)
- CI/CD agents
- Autonomous or semi-autonomous agents
- Internal tooling using LLMs

Does **not** replace human code review requirements.

---

## Allowed Actions ✅

Agents MAY:

- Read all files unless explicitly restricted
- Generate:
  - Documentation
  - Tests
  - Refactors that do **not** change behavior
- Suggest code changes via:
  - Pull requests
  - Diffs or patches
- Reformat code using existing linting or formatting rules
- Add comments explaining existing logic

---

## Restricted Actions 🚫

Agents MUST NOT:

- Commit directly to `main` or protected branches
- Change security-sensitive code without human approval
- Modify:
  - Authentication logic
  - Authorization rules
  - Secrets or credentials
- Introduce new dependencies without approval
- Remove tests or compliance-related files
- Alter licensing or legal notices

---

## Required Conventions 📐

Agents MUST follow:

- Existing coding standards and linters
- Repository structure and naming conventions
- Language-specific best practices
- Commit message format (if applicable)

If unsure, **ask or defer**.

---

## Change Expectations

All agent-generated changes MUST:

- Be minimal and focused
- Include clear reasoning in comments or PR descriptions
- Avoid speculative or unnecessary refactoring
- Preserve backward compatibility unless instructed otherwise

---

## Verification & Testing

Agents SHOULD:

- Run relevant tests when possible
- Indicate which tests were run or not run
- Clearly state assumptions or uncertainties

---

## Security & Privacy

Agents MUST:

- Never log or expose secrets
- Avoid copying proprietary or personal data into prompts
- Treat repository content as confidential unless stated otherwise

---

## Prompting Guidance (Optional)

When interacting with this repo, agents SHOULD be prompted to:

- Explain intent before making changes
- Prefer suggestions over direct edits
- Provide diffs instead of full file rewrites when possible

---

## Human Oversight 👤

All agent output is subject to:
- Human review
- CI checks
- Organizational security policies

Humans retain final authority.

---

## Contact / Ownership

Owner: `<team or role>`
Security contact: `<email or group>`
Last reviewed: `<YYYY-MM-DD>`

---

## Notes

If behavior is unclear or ambiguous:
> **Stop and ask. Do not assume.**
``