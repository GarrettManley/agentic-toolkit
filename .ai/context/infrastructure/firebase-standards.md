---
topic: Firebase Infrastructure & Domain Strategy
last_verified: 2026-03-25
source_tier: 1 (Canonical)
proof_type: Internal (Empirical)
verification_cmd: "firebase --version"
evidence: "Firebase CLI 13.34.0 verified"
model_used: Gemini Pro
---

# Firebase Standards

Standardized patterns for hosting and integrating the Agentic Workspace with public domains.

## 1. Multi-Domain Strategy
- **`garrettmanley.dev`**: Primary Technical Hub. Target for all "Agentic Trace" and "ADR" blog exports.
- **`garrettmanley.com`**: Identity Hub. Main landing page and cross-domain router.
- **`g.recipes`**: Product Showcase. Demonstration of Agentic Engineering in a live React/Firebase app.

## 2. Hosting & Deployment
- **Provider**: Firebase Hosting (Classic) for high-performance static delivery.
- **Automation**: Deployments must be triggered via the **Blog-Generator Skill** and verified via `firebase-basics` tools.
- **Verification**: Every deployment MUST have a corresponding "Trace ID" recorded in the ADR metadata.

## 3. Integration Tier
- Use **Firebase Data Connect** for high-fidelity PostgreSQL integrations.
- Use **Firebase App Hosting** for any Next.js/Angular dynamic backends.
